# Kalman Filtering for field nulling
import numpy as np
from glob import glob 
import scipy.optimize as sciop
# from nulling_my_coils import comp_field_control, opm_fieldline_control, reset_baseline 
base_vec = np.array([57.5, 106.9, 3.2, 0.0, 0.0, 0.0, 0.0, 0.0])
rescale_step = np.array([1, 1, 1, 0.15, 0.15, 0.15, 0.15, 0.15])
# raw_rec = np.load("compensationField_test_Bx.npz")['fields']
# raw_comp = np.load("compensationField_test_Bx.npz")['compensations']
data_dir = glob('data/*optimizing_data*.npz'); print(len(data_dir))
# data_dir = glob('optimizing_data_**.npz')
raw_array = list()
for dir in data_dir:
    raw_array.append(np.load(dir))

#%% Variables to understand and limit gracoil settings
ch_names = ['Y','Z','X','dBy/dy','dBz/dy','dBz/dz','dBz/dx','dBy/dx']
coil_dBdI = np.array([0.4570,0.6372,0.9090,2.6369,2.6271,1.4110,4.8184,2.4500]) 
scales = np.array([1e-6,1e-6,1e-6,1e-6/100,1e-6/100,1e-6/100,1e-6/100,1e-6/100]) 
coil_dBdI = coil_dBdI*scales #in T/A(/cm) 
coil_R = np.array([19.52,13.93,12.16,18.48,16.67,14.18,10.39,8.51]) # Measured values, in Ohms
coil_dBdV = coil_dBdI / coil_R
min_voltage = -10
max_voltage = 10
def convert2volt(field,ch):
     return field / coil_dBdV[ch] * 1e-9

def kalman_filtering(baseline,num_sensors,tol,opm_data): 

    num_coils = baseline.shape[0]  # Adjust based on your coil setup

    state_dim = num_sensors * 3 + num_coils  # 3 components (x, y, z) per sensor

    # Kalman filter matrices !!!Side note these are crucial for getting kalman to function, and need to be computed from recording data!!!
    F = np.eye(state_dim)  # Assume no inherent field drift
    G = np.random.randn(state_dim, num_coils) * 0.01  # Coil influence model (to be calibrated)
    H = np.hstack((np.eye(num_sensors * 3), G[:num_sensors * 3, : ]))  # Measurement model
    Q = np.eye(state_dim) * 1e-5  # Process noise covariance
    R = np.eye(num_sensors * 3) * 1e-3  # Measurement noise covariance

    # Initialize state and covariance
    x = np.zeros((state_dim, 1))  # Initial field is assumed zero
    P = np.eye(state_dim) * 1e-3  # Initial uncertainty

    comp = 0
    def reset_baseline(comp,baseline):
        comp += 1
        return comp
    
    def get_fields(comp):
        return opm_data[:,:,comp]
    


    # Function to update Kalman filter
    def kalman_update(measured_field, x, P):
        measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Ensure correct shape
        
        # Prediction step
        x_pred = F @ x
        P_pred = F @ P @ F.T + Q

        # Measurement update
        K = P_pred @ H.T @ np.linalg.inv(H @ P_pred @ H.T + R)
        x = x_pred + K @ (measured_field - H @ x_pred)
        P = (np.eye(state_dim) - K @ H) @ P_pred

        # Extract coil current recommendations
        coil_states = x[num_sensors * 3: num_sensors * 3 + num_coils].reshape((num_coils, 1))  # Ensure correct shape
        optimal_currents = -np.linalg.pinv(G[num_sensors * 3:, :]) @ coil_states  # Adjust current based on state

        return optimal_currents, x, P

    # Example usage
    measured_field = get_fields(comp) 
    measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Reshape to match expected dimensions
    
    obj_eval = np.copy(measured_field)
    limit = True; fail_safe = 0
    # for n in range(tol):
    while limit:
        optimal_coil_currents, x, P = kalman_update(measured_field, x, P)
        print("Recommended coil currents:", optimal_coil_currents.flatten())
        comp = reset_baseline(comp,optimal_coil_currents)
        measured_field = get_fields(comp)
        measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Reshape to match expected dimensions
        squared_difference = np.sum(measured_field**2 - obj_eval[:,-1]**2)
        print(f'Squared Difference: {squared_difference}')
        obj_eval = np.append(obj_eval,measured_field,axis=1)
        if squared_difference < tol or fail_safe > 8:
            limit = False


    result = sciop.OptimizeResult()
    result.fun = np.sum(obj_eval**2,axis=0)
    result.message = "complete"
    result.x = optimal_coil_currents

    return result

idx = 0
baseline = raw_array[idx]['base_array'][:,:-1]
opm_data = raw_array[idx]['data_array']

idy = 0
tol = 50
res = kalman_filtering(baseline[idy,:],16,tol,opm_data)
print(res.fun)
print(np.all([np.abs(convert2volt(i,n))<10 for n,i in enumerate(res.x)]))

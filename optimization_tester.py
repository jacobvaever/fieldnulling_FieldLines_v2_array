#%% Imports and global variables
import numpy as np
from glob import glob 
from scipy.optimize import minimize, nnls, lsq_linear, dual_annealing, differential_evolution
# from nulling_my_coils import comp_field_control, opm_fieldline_control, reset_baseline 
base_vec = np.array([57.5, 106.9, 3.2, 0.0, 0.0, 0.0, 0.0, 0.0])
rescale_step = np.array([1, 1, 1, 0.15, 0.15, 0.15, 0.15, 0.15])
# raw_rec = np.load("compensationField_test_Bx.npz")['fields']
# raw_comp = np.load("compensationField_test_Bx.npz")['compensations']
data_dir = glob('..\\OPM_automation_n_recording\\data\\*optimizing_data*.npz'); print(len(data_dir))
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

#%% Optimization 

# baseline = np.concatenate((np.tril(np.ones((9,8)),-1)*rescale_step + base_vec, np.ones((9,1))),axis=1) # Initial guess
nChans = 16 # maximum number of channels
# data = np.empty((nChans,3,9),float) # preallocate memory for data collected from changing the gradients
# for j in range(9): # number of test baselines, i.e., size(baseline,2)
    # if j !=  0:
        # comp_main.setOffset(j-1,baseline[j,j-1])
        # print([j-1, baseline[j,j-1]])
    # opm_main.fine_zero_sensors()
    # data[:,:,j] = opm_main.get_fields()
    # data[:,:,j] = raw_rec[:,:,j]
baseline = raw_array[0]['base_array']
data = raw_array[0]['data_array']

fail_ch = np.where(np.array([np.any(np.isnan(data[j,:,:])) for j in range(16)]))
# print(fail_ch) # channels that have a failed instance and should be removed!!!

data = np.delete(data,fail_ch, axis=0)
nChans = data.shape[0]
print(f'{nChans} channels left!')

def objective_RMS(opm_main,printout=False,output=None,verbose=True):
    # opm_main.fine_zero_sensors(verbose=verbose)
    # tmp = opm_main.get_fields()
    tmp = opm_main # placeholder to getting fields
    if printout:
        print(f'\nRMS of x fields: {np.sqrt(np.nanmean(tmp[:,0]**2))}')
        print(f'RMS of y fields: {np.sqrt(np.nanmean(tmp[:,1]**2))}')
        print(f'RMS of z fields: {np.sqrt(np.nanmean(tmp[:,2]**2))}')
    match output:
        case 'all':
            return np.array([np.sqrt(np.nanmean(tmp[:,0]**2)),
                            np.sqrt(np.nanmean(tmp[:,1]**2)),
                            np.sqrt(np.nanmean(tmp[:,2]**2))]).mean()
        case 'x':
            return np.sqrt(np.nanmean(tmp[:,0]**2))
        case 'y':
            return np.sqrt(np.nanmean(tmp[:,1]**2))
        case 'z':
            return np.sqrt(np.nanmean(tmp[:,2]**2))
        case _:
            return np.array([np.sqrt(np.nanmean(tmp[:,0]**2)),
                            np.sqrt(np.nanmean(tmp[:,1]**2)),
                            np.sqrt(np.nanmean(tmp[:,2]**2))])

def objective_var(opm_main,printout=False):
    # opm_main.fine_zero_sensors()
    # tmp = opm_main.get_fields()
    tmp = opm_main # placeholder to getting fields
    out = np.array([
        np.nanvar(tmp[:,0]),
        np.nanvar(tmp[:,1]),
        np.nanvar(tmp[:,2])
    ])
    if printout:
        print(f'Variance of x fields: {out[0]}')
        print(f'Variance of y fields: {out[1]}')
        print(f'Variance of z fields: {out[2]}')
    return out

def sarangs_double_lsq_algorithm(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline,residuals,rank,s = np.linalg.lstsq(np.transpose(Lvec),-offsets,rcond=None)
    print(residuals)#; print(rank); print(s)
    return new_baseline

def nonneg_double_lsq_algorithm(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    weight = [1,1,1]
    for i in range(9):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    print(residuals)
    return new_baseline

def contrained_double_lsq_algorithm(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    bounds = (coil_dBdV*-10/1e-9,coil_dBdV*10/1e-9)
    new_baseline = lsq_linear(np.transpose(Lvec),offsets,bounds)
    print(new_baseline.cost)
    return new_baseline.x

def dual_annealing_algorithm(baseline,data,nChans):
    def model_me_Lvec(params):
        def get_data_array(params):
            i = np.random.random_integers(0,3,1)[0]
            global raw_array
            baseline = raw_array[i]['base_array']
            data = raw_array[i]['data_array']
            return baseline, data
        baseline, data = get_data_array(params)
        L = np.empty((9, 3, nChans))
        for k in range(nChans): # number of sensors
            L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
        Lvec = L.reshape(9,3*nChans)
        offsets = Lvec[-1,:]
        Lvec = np.delete(Lvec, -1, axis=0)
        return Lvec-offsets
    # print(model_me_Lvec(baseline,data,nChans))
    rng = 10
    bounds = [(baseline[0,i]-rng,baseline[0,i]+rng) for i in range(8)]    
    # bounds = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    # bounds = [(0,coil_dBdV[i]*10/1e-9) for i in range(8)]
    def model_me_baby(params):
        tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
        return data[:,:,np.argmin(tmp)]

    def obj_fun(params):
        weight = [.5, .5, 1]
        # return np.nansum(model_me_baby(params)[-1,:].flatten()**2)
        return np.nanmean((model_me_baby(params)*weight).flatten()**2)
        # return np.nansum(model_me_Lvec(params).flatten()**2)

    result = dual_annealing(obj_fun,bounds,maxiter=1000,initial_temp=10000,x0=baseline[0,0:-1])
    print(result.fun)
    return result.x

def differential_evolution_algorithm(baseline,data,nChans):
    bounds = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    # rng = 10
    # bounds = [(baseline[0,i]-rng,baseline[0,i]+rng) for i in range(8)]
    # bounds = [(0,coil_dBdV[i]*10/1e-9) for i in range(8)]
    def model_me_baby(params):
        tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
        return data[:,:,np.argmin(tmp)]

    def obj_fun(params):
        weight = [.5, .5, 1]
        # return np.nansum(model_me_baby(params)[-1,:].flatten()**2)
        return np.nanmean((model_me_baby(params)*weight).flatten()**2)
        # return np.nansum(model_me_Lvec(params).flatten()**2)

    result = differential_evolution(obj_fun,bounds,maxiter=1000,x0=baseline[0,0:-1])
    print(result.fun)
    return result.x

def model_me_baby(params):
    tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
    return data[np.argmin(tmp),:,:]

def nonlinear_nulling_by_black_box(params,x,nChans):
    target = np.zeros(x.shape)

    def model_fake(params):
        tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
        # tmp = [np.abs(np.sum(params-baseline2[i,:])) for i in range(8)]
         
        return data[:,:,np.argmin(tmp)]
        # return data2['data'][:,:,np.argmin(tmp)]

    def objective_fun(params):
        # residuals = 0
        # for sensor_data in data:
        #     for axis_data in sensor_data:
        #         residuals += axis_data**2
        # return residuals
        x = model_fake(params)
        return np.nansum(x.flatten()**2) # it does the same as above
    
    # def constraint_positive(params, data, target):
    #     residuals = target - data
    #     return residuals
    
    bound = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    
    # result = minimize(objective_fun,params,args=(x,target),method='L-BFGS-B')
    result = minimize(objective_fun, params,bounds=bound, method='Nelder-Mead')
    print(result)
    return result.x

def nonlinear_nulling_by_hybrid(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)

def nonlinear_nulling_by_nelder_mead(baseline,opm_main,comp_main):
        # Objective function that uses real measurements of the magnetic field
        def get_magnetic_field(params):
            reset_baseline(comp_main,params)
            return opm_main.get_fields()

        def objective_function(params):
            B_measured = get_magnetic_field(params)  # This function should interact with your system to get measured fields
            B_target = 0  # Zero field in all directions [so kind of useless]
            return sum((B_measured - B_target)**2)

        # initial_guess = [0.1] * 8  # Initial guess for gradient parameters

        result = minimize(objective_function, baseline, method='Nelder-Mead')
        return result.x


#%% Execution of the different optimizers
# print(sarangs_double_lsq_algorithm(baseline,data,nChans))
print(nonneg_double_lsq_algorithm(baseline,data,nChans))
# print(contrained_double_lsq_algorithm(baseline,data,nChans))
# print(np.round(nonlinear_nulling_by_black_box(baseline[0,0:-1],data,nChans),2))
print(dual_annealing_algorithm(baseline,data,nChans))
print(differential_evolution_algorithm(baseline,data,nChans))

#%% creating a sample data set to give the optimizers
idx = 0
baseline = raw_array[idx]['base_array']
data = raw_array[idx]['data_array']
# print(sarangs_double_lsq_algorithm(baseline,data,nChans))
print(np.round(nonneg_double_lsq_algorithm(baseline,data,nChans),2))
# print(contrained_double_lsq_algorithm(baseline,data,nChans))
# print(np.round(nonlinear_nulling_by_black_box(baseline[0,0:-1],data,nChans),2))
print(dual_annealing_algorithm(baseline,data,nChans))


#%% test a hybrid solution
bounds = (coil_dBdV*-10/1e-9,coil_dBdV*10/1e-9)
def model_me_baby(params,x):
    tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
    return data[x,:,np.argmin(tmp)]



def obj_fun(params,x):
    return np.sum(model_me_baby(params,x).flatten()**2)

L = np.empty((8, nChans))
x = list(range(nChans))    
for k in range(nChans): # number of sensors
    L[:,k] = minimize(obj_fun,baseline[0,0:-1],args=(k),method='Nelder-Mead').x
# np.linalg.lstsq()
# Lvec = L.reshape(8,3*nChans)
# offsets = Lvec[-1,:]
# Lvec = np.delete(Lvec, -1, axis=0)
#%%
# def model_fun(param,grad):
#     tmp = [np.abs(np.sum(param-baseline[i,grad])) for i in range(8)]
#     return data[:,grad,np.argmin(tmp)]

#%%
idx = 1
baseline = raw_array[idx]['base_array']
data = raw_array[idx]['data_array']
def model_lsq(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    weight = [1,1,2]
    for i in range(9):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)

    print(f'New Gradients: {np.round(new_baseline,2)}\nResulting objective value: {residuals}')

#%% New method using residual contraint optimization
def nonneg_residual_lsq_algorithm(coil_settings, data, weight = [0.5, 0.5, 1.]):
    """
    Potential problems with this approach:

    * CONTRAINTS FOR THE OPTIMISATION: As close to zero and on the same side of zero for each sensors (positive)

                * The idea is that this forces the optimisation also to minimise the gradients

                * Here the assumption is that all the sensors are pointing in the same direction

                * This would not work well with sensors that are pointing in opposite direction

                * One could run the optimisation on a set of sensors pointing in somewhat the same direction
    """
    # Check dimensions of coil_settings
    if coil_settings.ndim != 2:
        raise ValueError(f"coil_settings must be a 2D array, but got shape {coil_settings.shape}")

    # Check dimensions of data
    if data.ndim != 3:
        raise ValueError(f"data must be a 3D array, but got shape {data.shape}")

    # Extract dimensions
    n_channels = data.shape[0]
    n_coil_settings = coil_settings.shape[0]
    n_coil_parameters = coil_settings.shape[1]
    L = np.empty((n_coil_parameters, 3, n_channels))
    if weight:
        for i in range(n_coil_settings):
            data[:,:,i] = data[:,:,i] * weight

    # Compute least squares
    for k in range(n_channels):
        L[:, :, k] = np.linalg.lstsq(coil_settings, np.transpose(np.squeeze(data[k, :, :])), rcond=None)[0]
    Lvec = L.reshape(n_coil_parameters, 3 * n_channels)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    
    def obj_val(baseline, Lvec, offsets):


        # squared error
        squared_error = np.sum((Lvec.T @ baseline + offsets)**2)

        # penalty for negative residuals
        penalty = np.sum((Lvec.T @ baseline + offsets) < 0) + 1

        # print(penalty)
        return squared_error*penalty
    
    def constraint(baseline,Lvec, offsets):
        return np.sum((Lvec.T @ baseline + offsets) < 0)

    # new_coil_settings = minimize(obj_val, coil_settings[0,:-1], args=(Lvec,offsets), constraints={'type': 'eq', 'fun': constraint, 'args': (Lvec,offsets)})
    new_coil_settings = minimize(obj_val, coil_settings[0,:-1], args=(Lvec, offsets), method="Nelder-Mead")#, constraints={'type': 'eq', 'fun': constraint, 'args': (Lvec, offsets)})

    return new_coil_settings

# Test the alg. 
idx = -1
# for idx in range(len(raw_array)):
for qq in range(1): 
    baseline = raw_array[idx]['base_array']
    data = raw_array[idx]['data_array']
    result = nonneg_residual_lsq_algorithm(baseline,data)
    print(f'{result.message}, objval: {result.fun:.2f} ')
    # print(f'Coil settings: {[f"{x:.2f}" for x in result.x]},\t Objective Value: {result.fun:.2f}')

#%% Second try on dual annealing
def dual_annealing_residuals(baseline,data):
    def model_me_Lvec(baseline,data):

        n_channels = data.shape[0]

        weight = [.5, .5, 1]
        for i in range(9):
            data[:,:,i] = data[:,:,i] * weight

        L = np.empty((9, 3, n_channels))
        for k in range(n_channels): # number of sensors
            L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
        Lvec = L.reshape(9,3*n_channels)
        offsets = Lvec[-1,:]
        Lvec = np.delete(Lvec, -1, axis=0)
        return Lvec, offsets
    Lvec, offsets = model_me_Lvec(baseline,data)
    # rng = 10
    # bounds = [(baseline[0,i]-rng,baseline[0,i]+rng) for i in range(8)]    
    bounds = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    # bounds = [(0,coil_dBdV[i]*10/1e-9) for i in range(8)]

    def obj_fun(baseline, Lvec, offsets):
        # squared error
        squared_error = np.sum((Lvec.T @ baseline + offsets)**2)

        # penalty for negative residuals
        penalty = np.sum((Lvec.T @ baseline + offsets) < 0) + 1

        # print(squared_error*penalty)
        return squared_error*penalty
        

    result = differential_evolution(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1])
    result = dual_annealing(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1])
    # result = differential_evolution(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1],maxfun=10000000,maxiter=10000)
    print(result.fun)
    return result.x

idx = 0
baseline = raw_array[idx]['base_array']
data = raw_array[idx]['data_array']
result = dual_annealing_residuals(baseline,data)
print(result)

#%% Kalman filter edition (instead of LSQ.)
idx = 0
baseline = raw_array[idx]['base_array']
data = raw_array[idx]['data_array']

num_sensors = data.shape[0]
num_coils = baseline[0,:-1].shape[0]  # Adjust based on your coil setup

state_dim = num_sensors * 3 + num_coils  # 3 components (x, y, z) per sensor

# Kalman filter matrices
F = np.eye(state_dim)  # Assume no inherent field drift
G = np.random.randn(state_dim, num_coils) * 0.01  # Coil influence model (to be calibrated)
H = np.hstack((np.eye(num_sensors * 3), G[:num_sensors * 3, : ]))  # Measurement model
Q = np.eye(state_dim) * 1e-5  # Process noise covariance
R = np.eye(num_sensors * 3) * 1e-3  # Measurement noise covariance

# Initialize state and covariance
x = np.zeros((state_dim, 1))  # Initial field is assumed zero
P = np.eye(state_dim) * 1e-3  # Initial uncertainty

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
idy = 0
measured_field = data[:,:,idy]
# x = np.transpose([np.append(measured_field,baseline[idy,:-1])])

# Is there Kalman iterative??
measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Reshape to match expected dimensions
optimal_coil_currents, x, P = kalman_update(measured_field, x, P)
print("Recommended coil currents:", optimal_coil_currents.flatten()) 


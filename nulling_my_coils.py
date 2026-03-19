import sys, time
import queue
import logging
import argparse
import numpy as np
from os import system
from bitarray import bitarray, util
from scipy.io import savemat
from scipy.linalg import svd 
from scipy.optimize import minimize, nnls, lsq_linear, dual_annealing, differential_evolution, OptimizeResult
sys.path.append('Source')
from com_monitor import ComMonitorThread
from fieldline_api.fieldline_service import FieldLineService


# NB: change the opm:fieldline_control class to a "with as" statement to optimize exec time!!!
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Include debug-level logs.")
parser.add_argument("-i", '--ip', type=lambda x: x.split(","), help="comma separated list of IPs", required=True)
args = parser.parse_args()

stream_handler = logging.StreamHandler()
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(threadName)s(%(process)d) %(message)s [%(filename)s:%(lineno)d]',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG if args.verbose else logging.ERROR,
    handlers=[stream_handler]
)

ip_list = args.ip
print(f"Connecting to IPs: {ip_list}")
class opm_fieldline_control:
    def __init__(self):
        # self.service = service
        self.done = False
        self.sample_counter = 0

        self.rt_data_timer = 0
        self.rt_data = []
 
    def call_done(self):
        # self.done
        self.done = True

    def restart_sensors(self,verbose=True):                
        # Restart all sensors
        self.done = False
        # Get dict of all the sensors
        sensors = service.load_sensors()
        if verbose:
            print(f"Got sensors: {sensors}")
        # Make sure closed loop is set
        service.set_closed_loop(False)
        if verbose:
            print("Doing sensor restart")
        # Do the restart
        if verbose:
            service.restart_sensors(sensors, on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished restart'), on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: self.call_done())
        else:
            service.restart_sensors(sensors,on_completed=lambda: self.call_done())
        while not self.done:
            time.sleep(0.5)
            
    def coarse_zero_sensors(self,verbose=True):
        # Coarse zero all sensors 
        self.done = False
        sensors = service.load_sensors()
        # time.sleep(2)
        if verbose:
            print("Doing coarse zero")
            service.coarse_zero_sensors(sensors, on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'), on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: self.call_done())
        else:
            service.coarse_zero_sensors(sensors, on_completed=lambda: self.call_done())

        while not self.done:
            time.sleep(0.5)

    def fine_zero_sensors(self, verbose=True):
        # Fine zero all sensors
        self.done = False
        sensors = service.load_sensors()
        if verbose:
            print("Doing fine zero")
            service.fine_zero_sensors(sensors,
                                      #    on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                      on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: self.call_done())
        else:
            service.fine_zero_sensors(sensors, on_completed=lambda: self.call_done())

        while not self.done:
            time.sleep(0.5)


    def get_fields(self):
        # get x/y/z fields from sensors
        # tmp = time.time()
        sensors = service.load_sensors()
        fields = np.empty((16,3),float)
        for idx,ch in enumerate(sensors[0]):
            fields[idx,:] = service.get_fields(0,ch)
        # fields = service.get_fields(0,1)
        # print(f"Got fields from: {sensors}")
        # print(time.time()-tmp)
        return fields
    
    def test_RT_data(self):
        # Test real-time data collection
        def print_bz(data):
            # data is a predefined input for the callback function
            # it is a nested dict of data collected!!!
            # and data from data is in femto tesla
            self.sample_counter += 1
            for key in data['data_frames'].items():
                # print(f"{key}: {field['sensor_id']}")
                print(f"{key[1]['sensor_id']}: {key[1]['data']}")
        service.read_data(print_bz)
        service.start_adc(0)
        start = time.time()
        while time.time() - start < 1.0:
            time.sleep(0.5)
        service.stop_adc(0)
        service.read_data()
        print("Read %d samples"% self.sample_counter)
        self.sample_counter = 0
        
    def start_data(self):
        # start data acquisition from sensors
        def print_bz(data):
            self.sample_counter += 1
            self.rt_data.append(data)
        service.read_data(print_bz)
        service.start_adc(0)
        self.rt_data_timer = time.time()
    
    def stop_data(self):
        # stop data acquisition from sensors
        self.rt_data_timer = time.time() - self.rt_data_timer
        service.stop_adc(0)
        service.read_data()
        print("Read %d samples"% self.sample_counter)
        print(self.rt_data_timer)
        self.sample_counter = 0


    def turn_off_sensors(self):
        # Turn off all the sensors
        sensors = service.load_sensors()
        service.turn_off_sensors(sensors)

    def check_sensor_error(self):
            fix_idx = [service.get_sensor_state(0,ch+1).name == 'SENSOR_ERROR' for ch in range(16)]
            if any(fix_idx):
                try:
                    self.coarse_zero_sensors()
                    self.fine_zero_sensors()
                except:
                    print('Sensors failed at restart!')
                    self.restart_sensors()
                    self.coarse_zero_sensors()
                    self.fine_zero_sensors()


## Compensation coil variables 
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
def over_limit_check(coil_settings):
    return np.all([np.abs(convert2volt(i,n))<10 for n,i in enumerate(coil_settings)])

class comp_field_control:
    def __init__(self):
        self.tx_q = queue.Queue(maxsize=10000)
        self.rx_q = queue.Queue(maxsize=10000)
        self.monitor_msg_q = queue.Queue(maxsize=100)
        self.ser_monitor = ComMonitorThread('ZEROFIELD',
                                            self.tx_q,
                                            self.rx_q,
                                            self.monitor_msg_q,
                                            'auto',
                                            921600,
                                            verbose=None,
                                            exc_callback = None)
        time.sleep(3)
        self.ser_monitor.start()

    def setOffset(self, ch, field, verbose=True, delay=0.1):

        value = field / coil_dBdV[ch] * 1e-9
        
        if verbose:
            print("%s (CH%d): offset magnetic field %.6f nT"%(ch_names[ch], ch+1, field))
            # print("%s (CH%d): offset voltage %.6f V"%(ch_names[ch], ch+1, value))
        cmdbyte = util.int2ba(ch, length=8).tobytes()
        
        uintbytes= util.int2ba(int((2**19-1) * -value/10 + (2**19-1)), length=32).tobytes()
        
        # if verbose:
        #     print(cmdbyte + uintbytes[::-1])
            
        self.tx_q.put_nowait(cmdbyte + uintbytes[::-1])
        time.sleep(delay)

    def print_rx(self):
    
        if not self.rx_q.empty():
            rx_data = self.rx_q.get_nowait()
        
            print("Rx:")
            print(rx_data)

# Maybe define this as a class [coil_nulling] !!!!?
def reset_baseline(comp_main,baseline):
    comp_main.setOffset(0,baseline[0]) 
    comp_main.setOffset(1,baseline[1]) 
    comp_main.setOffset(2,baseline[2]) 
    comp_main.setOffset(3,baseline[3]) 
    comp_main.setOffset(4,baseline[4]) 
    comp_main.setOffset(5,baseline[5]) 
    comp_main.setOffset(6,baseline[6]) 
    comp_main.setOffset(7,baseline[7]) 
    time.sleep(2) # how important was this delay again????
    # comp_main.ser_monitor.join()

def objective_RMS(opm_main,printout=False,output=None,verbose=True):
    opm_main.fine_zero_sensors(verbose=verbose)
    tmp = opm_main.get_fields()
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
        
def Collect_data_array(base_vec,rescale_step):
    baseline = np.concatenate((np.tril(np.ones((9,8)),-1)*rescale_step + base_vec, np.ones((9,1))),axis=1) # Initial guess
    nChans = 16 # maximum number of channels
    data = np.empty((nChans,3,9),float) # preallocate memory for data collected from changing the gradients
    for j in range(9): # number of test baselines, i.e., size(baseline,2)
        if j !=  0:
            comp_main.setOffset(j-1,baseline[j,j-1])
            # print([j-1, baseline[j,j-1]])
        opm_main.fine_zero_sensors()
        data[:,:,j] = opm_main.get_fields()
        # data[:,:,j] = raw_rec[:,:,j]

    fail_ch = np.where(np.array([np.any(np.isnan(data[j,:,:])) for j in range(16)]))
    # print(fail_ch) # channels that have a failed instance and should be removed!!!

    data = np.delete(data,fail_ch, axis=0)
    nChans = data.shape[0]
    print(f'{nChans} channels left!')
    return baseline, data, nChans

def save_optimize_data(baseline,name):
    data = opm_main.get_fields()
    np.savez(f'comp_alg_data/{name}',baseline=baseline,data=data)


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
    weight = [.5,.5,1]
    for i in range(9):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    # s_val = svd(Lvec,compute_uv=False); print(s_val)
    print(residuals)
    return new_baseline

def nonneg_residual_lsq_algorithm(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    weight = [.5,.5,1]
    for i in range(9):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    def obj_val(baseline,Lvec,offsets):
        return np.sum((Lvec.T @ baseline + offsets)**2)
    
    def constraint(baseline,Lvec, offsets):
        return np.sum((Lvec.T @ baseline + offsets) < 0)
    new_baseline = minimize(obj_val,baseline[0,:-1],args=(Lvec,offsets),constraints={'type': 'eq', 'fun': constraint, 'args': (Lvec,offsets)})
    

    # new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    # s_val = svd(Lvec,compute_uv=False); print(s_val)
    # print(residuals)
    print(new_baseline)
    return new_baseline.x

def contrained_double_lsq_algorithm(baseline,data,nChans):
    L = np.empty((9, 3, nChans))
    weight = [.5,.5,1]
    for i in range(9):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(9,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    bounds = (np.zeros(8),coil_dBdV*9/1e-9)
    # bounds = (coil_dBdV*-10/1e-9,coil_dBdV*10/1e-9)
    new_baseline = lsq_linear(np.transpose(Lvec),-offsets,bounds)
    print(new_baseline.cost)
    return new_baseline.x

def nonlinear_nulling_by_black_box(baseline,data,base_array):
    # target = np.zeros(data.shape)

    def model_fake(params):
        tmp = [np.abs(np.sum(params-base_array[i,0:-1])) for i in range(8)]
        return data[:,:,np.argmin(tmp)]

    def objective_fun(params):
        x = model_fake(params)
        return np.sum(x.flatten()**2)
    
    # def constraint_positive(params, data, target):
    #     residuals = target - data
    #     return residuals
    
    bound = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    
    # result = minimize(objective_fun,params,args=(x,target),method='L-BFGS-B')
    result = minimize(objective_fun,baseline,bounds=bound,method='Nelder-Mead')
    print(result)
    return result.x

last_fval = np.inf
def nonlinear_nulling_by_nelder_mead(baseline):
        # Objective function that uses real measurements of the magnetic field
        def get_magnetic_field(params):
            reset_baseline(comp_main,params)
            # opm_main.restart_sensors()
            opm_main.coarse_zero_sensors()
            objective_RMS(opm_main,printout=True)
            return opm_main.get_fields()

        def objective_function(params):
            global last_fval
            B_measured = get_magnetic_field(params)  # This function should interact with your system to get measured fields
            # B_target = 0  # Zero field in all directions [so kind of useless]
            weight = [.5, .5, 1]
            obj_val = np.nanmean(((B_measured*weight).flatten())**2)
            print(last_fval-obj_val); last_fval = obj_val
            return obj_val

        # initial_guess = [0.1] * 8  # Initial guess for gradient parameters

        result = minimize(objective_function,baseline,method='Nelder-Mead',options={'maxiter': 2,'maxfev': 16, 'adaptive': True})
        # result = minimize(objective_function,baseline,method='Powell',options={'maxiter': 2})
        # result = minimize(objective_function,baseline,method='L-BFGS-B',options={'maxiter': 2})
        return result.x

def nonlinear_nulling_by_dual_annealing(baseline):
        global rescale_step
        # Objective function that uses real measurements of the magnetic field
        def get_magnetic_field(params):
            reset_baseline(comp_main,params)
            opm_main.restart_sensors()
            opm_main.coarse_zero_sensors()
            objective_RMS(opm_main,printout=True)
            return opm_main.get_fields()

        def objective_function(params):
            global last_fval
            B_measured = get_magnetic_field(params)  # This function should interact with your system to get measured fields
            # B_target = 0  # Zero field in all directions [so kind of useless]
            weight = [.5, .5, 1]
            obj_val = np.nanmean(((B_measured*weight).flatten())**2)
            # obj_val = np.nansum(((B_measured[-1,:]).flatten())**2)
            print(f'Objective value: {obj_val}; difference from last iteration: {last_fval-obj_val}'); last_fval = obj_val
            return obj_val
        
        bound = [(baseline[i]-rescale_step[i]*10,baseline[i]+rescale_step[i]*10) for i in range(8)]
        # bound = [(coil_dBdV[i]*-5/1e-9,coil_dBdV[i]*5/1e-9) for i in range(8)]
        # bound = [(0,coil_dBdV[i]*8/1e-9) for i in range(8)]
        result = dual_annealing(objective_function,bound,maxiter=2,maxfun=16,x0=baseline)
        # result = differential_evolution(objective_function,bound,maxiter=2,x0=baseline)
        return result.x

def offline_differential_evolution(baseline,data,nChans):
    bounds = [(coil_dBdV[i]*-10/1e-9,coil_dBdV[i]*10/1e-9) for i in range(8)]
    def model_me_baby(params):
        tmp = [np.abs(np.sum(params-baseline[i,0:-1])) for i in range(8)]
        return data[:,:,np.argmin(tmp)]
    def obj_fun(params):
        weight = [.5, .5, 1]
        return np.mean((model_me_baby(params)*weight).flatten()**2)
    result = differential_evolution(obj_fun,bounds,maxiter=8,x0=baseline[0,0:-1])
    print(result.fun)
    return result.x

def multi_nonlinlsq_nulling(baseline,rescale_step):
        def objective_function(baseline,rescale_step):
            base_array, data_array, nChans = Collect_data_array(baseline,rescale_step)
            # np.savez('data/optimizing_data_3-1',base_array=base_array,data_array=data_array)
            new_baseline = nonneg_double_lsq_algorithm(base_array,data_array,nChans)
            # new_baseline = contrained_double_lsq_algorithm(base_array,data_array,nChans)
            new_baseline = np.round(new_baseline,2); print(new_baseline)
            reset_baseline(comp_main,new_baseline)
            opm_main.restart_sensors()
            opm_main.coarse_zero_sensors()
            # opm_main.fine_zero_sensors()  
            return objective_RMS(opm_main,output='all',printout=True)
        bounds = [(coil_dBdV[i]*-9/1e-9,coil_dBdV[i]*9/1e-9) for i in range(8)]
        result = minimize(objective_function,baseline,args=(rescale_step),bounds=bounds,
                          method='Nelder-Mead',options={'maxiter': 1, 'adaptive': True})
        return result.x

def homo_field_solver(baseline,data,nChans):
    data = data[:,:,:4]
    baseline = np.append(baseline[:4,:3],np.ones((4,1)),axis=1)
    L = np.empty((4, 3, nChans))
    weight = [.5,.5,1]
    for i in range(4):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(4,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    print(residuals)
    return new_baseline
def grad_field_solver(baseline,data,nChans):
    data = data[:,:,3:]
    baseline = np.append(baseline[3:,3:-1],np.ones((6,1)),axis=1)
    L = np.empty((6, 3, nChans))
    weight = [.5,.5,1]
    for i in range(6):
        data[:,:,i] = data[:,:,i]*weight
    for k in range(nChans): # number of sensors
        L[:,:,k] = np.linalg.lstsq(baseline,np.transpose(np.squeeze(data[k,:,:])),rcond=None)[0]
    Lvec = L.reshape(6,3*nChans)
    offsets = Lvec[-1,:]
    Lvec = np.delete(Lvec, -1, axis=0)
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    print(residuals)
    return new_baseline

def nonneg_residual_lsq_algorithm_alt(coil_settings, data, weight = [0.5, 0.5, 1.]):

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
    # new_coil_settings = minimize(obj_val, coil_settings[0,:-1], args=(Lvec, offsets), method="Nelder-Mead")
    new_coil_settings = minimize(obj_val, coil_settings[0,:-1], args=(Lvec, offsets), method="Nelder-Mead",options={"maxfev":10000000,"maxiter":10000})
    # print(new_coil_settings.fun)
    return new_coil_settings

def blackbox_nonneg_residuals(baseline,data,method="dualanne"):
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
        

    if method=="diffevol":
        # result = differential_evolution(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1])
        result = differential_evolution(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1],maxfun=10000000,maxiter=10000)
    else:
        # result = dual_annealing(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1])
        result = dual_annealing(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1],maxfun=10000000,maxiter=10000)

    # result = differential_evolution(obj_fun,bounds,args=(Lvec,offsets),x0=baseline[0,:-1],maxfun=10000000,maxiter=10000)
    # print(result.fun)
    return result

def kalman_filtering(baseline,num_sensors,tol,comp_main,opm_main): 

    num_coils = baseline.shape[0]  # Adjust based on your coil setup

    state_dim = num_sensors * 3 + num_coils  # 3 components (x, y, z) per sensor

    # Kalman filter matrices 
    '''
    NB: These matricies all needs to be computed from data in the lab!!
    e.g. G is just a matrix of random numbers  
    '''
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

    # Usage
    measured_field = opm_main.get_fields()
    measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Reshape to match expected dimensions
    
    obj_eval = np.copy(measured_field)
    limit = True; maxIter = 100; failSafe = 0
    # for n in range(tol): 
    while limit:
        optimal_coil_currents, x, P = kalman_update(measured_field, x, P)
        print("Recommended coil currents:", optimal_coil_currents.flatten())
        if over_limit_check:
            reset_baseline(comp_main,optimal_coil_currents)
            measured_field = opm_main.get_fields()
            measured_field = np.array(measured_field).reshape((num_sensors * 3, 1))  # Reshape to match expected dimensions
        squared_difference = np.sum(measured_field**2 - obj_eval[:,-1]**2)
        print(f'Squared Difference: {squared_difference}')
        obj_eval = np.append(obj_eval,measured_field,axis=1)
        
        if squared_difference < tol or failSafe > maxIter:
            limit = False # consider putting why it stops in the result message

    result = OptimizeResult()
    result.fun = np.sum(obj_eval**2,axis=0)
    result.message = "complete"
    result.x = optimal_coil_currents
    return result

        

with np.load('last_baseline.npz') as file:
    baseline = np.array([0,0,0,0,0,0,0,0]) # no compensation
    baseline = np.array([57.5,106.9,3.2,0,0,0,0,0]) # reliable initial guess
    #baseline = np.array([43.5,48.9,13.1,0,0,0,0,0]) 
    #baseline = file['optim_baseline']

    # baseline = np.array([34.63,37.46,10.53,0.0,0.0,0.16,0.19,0.0]) # Better version (05/10/24)
    # baseline = np.array([29.41, 44.62, 0.51, 0.0, 0.0, 0.03, 0.2, 0.39]) # Optimized (12/10/24)
    # baseline = np.array([31.18, 50.36, 5.11, 0., 0., 0., 0.68, 0.]) # optimized facing floor (15/11/24)
print(f"using following baseline: {baseline}")
rescale_step = np.array([1, 1, 1, 0.15, 0.15, 0.15, 0.15, 0.15])

# time.sleep(2*60)
duration = 1  # seconds
freq = 440  # Hz
# system('play -nq -t alsa synth {} sine {}'.format(duration, freq))

# initiate classes for both APIs
try:

    with  FieldLineService(ip_list) as service:
        opm_main = opm_fieldline_control()
        comp_main = comp_field_control()

        # Initiate OPMs
        reset_baseline(comp_main,baseline)
        opm_main.restart_sensors()
        opm_main.coarse_zero_sensors()
        objective_RMS(opm_main,printout=True)
        start_time = time.time()

        # new_baseline = multi_nonlinlsq_nulli        
        # base_array, data_array, nChans = Collect_data_array(baseline,rescale_step)
        # # np.savez('data/optimizing_data_3-1',base_array=base_array,data_array=data_array)
        # new_baseline = offline_differential_evolution(base_array,data_array,nChans)
        # new_baseline = np.round(new_baseline,2); print(new_baseline)
        # reset_baseline(comp_main,new_baseline)
        # opm_main.restart_sensors()
        # opm_main.coarse_zero_sensors()  
        # objective_RMS(opm_main,printout=True)ng(baseline,rescale_step)

        # method = ["nonnegres","dualanne","diffevol","kalman"]; m = 1; trial = 5
        method = ["nonnegres","dualanne","diffevol","kalman"]; m = 2; trial = 'subject_5'
        save_optimize_data(baseline,f'{method[m]}__before_{trial}')

        #-- Optimization content goes here!! --#
        n_iterations = 3
        m_iterations = [1,0]
        new_baseline = baseline
        # for i in range(n_iterations):
        for i,m in enumerate(m_iterations):
            if i<2:
                base_array, data_array, nChans = Collect_data_array(new_baseline,rescale_step)
            else:
                base_array, data_array, nChans = Collect_data_array(new_baseline,rescale_step/4)
            
            if method[m] == "nonnegres":
                result = nonneg_residual_lsq_algorithm_alt(base_array,data_array,nChans)
            elif method[m] == "dualanne":
                result = blackbox_nonneg_residuals(base_array,data_array,nChans)
            elif method[m] == "diffevol":
                result = blackbox_nonneg_residuals(base_array,data_array,nChans)
            elif method[m] == "kalman":
                result = kalman_filtering(baseline,nChans,3,comp_main,opm_main)

            new_baseline = np.round(result.x,2); print(f'{result.message}, objval: {result.fun:.2f} ')
            np.savez(f'comp_alg_data/optimizing_data_{trial}-{i+1}_{method[m]}',base_array=base_array,data_array=data_array,optimization=result)
            reset_baseline(comp_main,new_baseline)
            opm_main.restart_sensors()
            opm_main.coarse_zero_sensors() 
            objective_RMS(opm_main,printout=True)

        # base_array, data_array, nChans = Collect_data_array(new_baseline,rescale_step)
        # np.savez('data/optimizing_data_19-2',base_array=base_array,data_array=data_array)
        # new_baseline = nonneg_double_lsq_algorithm(base_array,data_array,nChans)
        # # # new_baseline = sarangs_double_lsq_algorithm(base_array,data_array,nChans)
        # # # new_baseline[3:] = grad_field_solver(base_array,data_array,nChans)
        # # new_baseline = np.round(new_baseline,2); print(new_baseline)
        # reset_baseline(comp_main,new_baseline)
        # opm_main.restart_sensors()
        # opm_main.coarse_zero_sensors()
        # # # opm_main.fine_zero_sensors()  
        # objective_RMS(opm_main,printout=True)

        # base_array, data_array, nChans = Collect_data_array(new_baseline,rescale_step/4)
        # np.savez('data/optimizing_data_19-3',base_array=base_array,data_array=data_array)
        # new_baseline = nonneg_double_lsq_algorithm(base_array,data_array,nChans)
        # # # new_baseline = sarangs_double_lsq_algorithm(base_array,data_array,nChans)
        # new_baseline = np.round(new_baseline,2); print(new_baseline)
        # reset_baseline(comp_main,new_baseline)
        # opm_main.restart_sensors()
        # opm_main.coarse_zero_sensors()
        # # # opm_main.fine_zero_sensors()  
        # objective_RMS(opm_main,printout=True)



        save_optimize_data(new_baseline,f'{method[m]}_after_{trial}')
        np.savez("last_baseline",optim_baseline=new_baseline)
        
        #-- real-time optimizer --# 
        # new_baseline = nonlinear_nulling_by_dual_annealing(new_baseline)
        # new_baseline = nonlinear_nulling_by_nelder_mead(new_baseline)

        # new_baseline = np.round(new_baseline,2); print(new_baseline)
        # reset_baseline(comp_main,new_baseline)
        # opm_main.restart_sensors()
        # opm_main.coarse_zero_sensors()
        # # opm_main.fine_zero_sensors()  
        # objective_RMS(opm_main,printout=True)

        #-- Recording of from the OPM sensors --#
        # opm_main.test_RT_data()
        # opm_main.start_data()
        # start = time.time()
        # tmp_baseline = baseline
        # for i in range(8):
        #     while time.time() - start < 1.0:
        #         time.sleep(0.5*60) # recording duration??
        #     tmp_baseline[i] += rescale_step[i]
        #     reset_baseline(comp_main,tmp_baseline)
        # opm_main.stop_data()
        # np.savez('data/dynamic_optimizer-4',DATA=opm_main.rt_data)     

        
        # service.open() # for some reason you need to reopen service eventhough it was opened at the with as statement?
        # END of optimization
        end_time = time.time()
        # time.sleep(5*60) # run additionally for 5x60 seconds
        system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
        system('spd-say "your program has finished"')
        print(f'Execution time: {end_time-start_time}s')   
        comp_main.ser_monitor.join()
except ConnectionError as e:
    logging.error("Failed to connect: %s" % str(e))
import sys, time
import queue
import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt
# from timeit import timeit
from datetime import datetime
from bitarray import bitarray, util
from progress.bar import Bar
sys.path.append('Source')
from com_monitor import ComMonitorThread
from fieldline_api.fieldline_service import FieldLineService
start_time = time.time()

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
        service.set_closed_loop(True)
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
            # self.rt_data.append(data)
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
ch_names = ['Y',
            'Z',
            'X',
            'dBy/dy',
            'dBz/dy',
            'dBz/dz',
            'dBz/dx',
            'dBy/dx']
coil_dBdI = np.array([0.4570,
                       0.6372,
                       0.9090,
                       2.6369,
                       2.6271,
                       1.4110,
                       4.8184,
                       2.4500]) 
scales = np.array([1e-6,
                    1e-6,
                    1e-6,
                    1e-6/100,
                    1e-6/100,
                    1e-6/100,
                    1e-6/100,
                    1e-6/100]) 
coil_dBdI = coil_dBdI*scales #in T/A(/cm) 
coil_R = np.array([19.52,
                   13.93,
                   12.16,
                   18.48,
                   16.67,
                   14.18,
                   10.39,
                   8.51
                   ]) #Measured values, in Ohms
coil_dBdV = coil_dBdI / coil_R
min_voltage = -10
max_voltage = 10

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

def reset_baseline(comp_main,baseline):
    comp_main.setOffset(0,baseline[0]) 
    comp_main.setOffset(1,baseline[1]) 
    comp_main.setOffset(2,baseline[2]) 
    comp_main.setOffset(3,baseline[3]) 
    comp_main.setOffset(4,baseline[4]) 
    comp_main.setOffset(5,baseline[5]) 
    comp_main.setOffset(6,baseline[6]) 
    comp_main.setOffset(7,baseline[7]) 
    time.sleep(2)
    # comp_main.ser_monitor.join()

def objective_fun(fieldline):
    fieldline.fine_zero_sensors()
    # np.nan_to_num()
    objective = np.linalg.norm(np.nan_to_num(fieldline.get_fields()))
    # time.sleep(0.5)
    return objective

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

def objective_var(opm_main,printout=False):
    opm_main.fine_zero_sensors()
    tmp = opm_main.get_fields()
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



def obj_tmp(opm_main):
    return objective_RMS(opm_main,output='all')

def check_optimize_one(opm_main,comp_main,baseline,CH=0,rms=False,direction=None):
    rescale_step = np.array([1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1])*5
    # rescale_step = np.array([3, 3, 3, 0.3, 0.3, 0.3, 0.3, 0.3])
    offset = baseline[CH]
    II = 11

    obj_val = np.empty(II,float)
    # field = np.linspace(-rescale_step[CH]*II,rescale_step[CH]*II,II)    
    field = np.linspace(-rescale_step[CH]*(II-1)/2,rescale_step[CH]*(II-1)/2,II)    
    for idx,step in enumerate(field):
        comp_main.setOffset(CH,offset+step)
        # time.sleep(0.1)
        # if idx == 0:
        #     opm_main.coarse_zero_sensors()
        if not rms:
            obj_val[idx] = objective_fun(opm_main)
        else:
            match direction:
                case 'x':
                    obj_val[idx] = objective_RMS(opm_main)[0]
                case 'y':
                    obj_val[idx] = objective_RMS(opm_main)[1]
                case 'z':
                    obj_val[idx] = objective_RMS(opm_main)[2]
                case _:
                    obj_val[idx] = np.mean(objective_RMS(opm_main))
    print(field+offset)
    print(obj_val)
    # comp_main.setOffset(CH,offset+field[np.argmin(obj_val)]) # set to optimal
    # comp_main.setOffset(CH,offset) # reset
    # time.sleep(0.1)
    # comp_main.ser_monitor.join()
    # opm_main.fine_zero_sensors()
    return field+offset, obj_val

def twosided_check_optimize_one(opm_main,comp_main,baseline,CH=0,objective_fun=objective_fun):
    # print(obj_val.shape)
    # sufficient = 60 # stop criteria
    # random walk from all params or random step from one at a time? 
    # regularization of new objective value?
    # rng = np.random.default_rng()
    rescale_step = np.array([[1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1],
                             [5, 5, 5, 0.5, 0.5, 0.5, 0.5, 0.5]])
    II = 0
    chosen_x = 0

    offset = baseline[CH]
    step = rescale_step[:,CH]
    # step_taken = np.empty(1)
    step_taken = []
    obj_val = np.empty((5,1),float)
    comp_main.setOffset(CH,offset-step[1])
    obj_val[0,II] = objective_fun(opm_main)
    comp_main.setOffset(CH,offset-step[0])
    obj_val[1,II] = objective_fun(opm_main)
    comp_main.setOffset(CH,offset)
    obj_val[2,II] = objective_fun(opm_main)
    comp_main.setOffset(CH,offset+step[0])
    obj_val[3,II] = objective_fun(opm_main)
    comp_main.setOffset(CH,offset+step[1])
    obj_val[4,II] = objective_fun(opm_main)
    # original_val = obj_val[0,0]
    # def where_to_go(obj_val):
        # return np.argmin(obj_val[])
    while II <= 10:
        step_taken.append(np.argmin(obj_val[:,II]))
        obj_val = np.append(obj_val,np.zeros((5,1)),axis=1)
        match step_taken[II]:

            case 0: # if optimal location is X-h_l
                chosen_x = 0
                offset = offset-step[1]
                comp_main.setOffset(CH,offset-step[1])
                obj_val[0,II+1] = objective_fun(opm_main)
                comp_main.setOffset(CH,offset-step[0])
                obj_val[1,II+1] = objective_fun(opm_main)
                obj_val[2,II+1] = obj_val[0,II]
                comp_main.setOffset(CH,offset+step[0])
                obj_val[3,II+1] = objective_fun(opm_main)
                obj_val[4,II+1] = obj_val[2,II]

            case 1: # if optimal location is X-h_s
                chosen_x = 0
                offset = offset-step[0]
                comp_main.setOffset(CH,offset-step[1])
                obj_val[0,II+1] = objective_fun(opm_main)
                comp_main.setOffset(CH,offset-step[0])
                obj_val[1,II+1] = objective_fun(opm_main)
                obj_val[2,II+1] = obj_val[1,II]
                obj_val[3,II+1] = obj_val[2,II]
                comp_main.setOffset(CH,offset+step[1])
                obj_val[4,II+1] = objective_fun(opm_main)

            case 2: # if optimal location is X
                # print('X was best!')
                # break
                if chosen_x > 0:
                    print('choose X twice!')
                    break
                else:
                    chosen_x = 1
                # step = -step
                    comp_main.setOffset(CH,offset-step[1])
                    obj_val[0,II+1] = objective_fun(opm_main)
                    comp_main.setOffset(CH,offset-step[0])
                    obj_val[1,II+1] = objective_fun(opm_main)
                    obj_val[2,II+1] = obj_val[2,II]
                    comp_main.setOffset(CH,offset+step[0])
                    obj_val[3,II+1] = objective_fun(opm_main)
                    comp_main.setOffset(CH,offset+step[1])
                    obj_val[4,II+1] = objective_fun(opm_main)
                
            case 3: # if optimal location is X+h_s
                chosen_x = 0
                offset = offset+step[0]
                comp_main.setOffset(CH,offset-step[1])
                obj_val[0,II+1] = objective_fun(opm_main)
                obj_val[1,II+1] = obj_val[0,II]
                obj_val[2,II+1] = obj_val[3,II]
                comp_main.setOffset(CH,offset+step[0])
                obj_val[3,II+1] = objective_fun(opm_main)
                comp_main.setOffset(CH,offset+step[1])
                obj_val[4,II+1] = objective_fun(opm_main)
            
            case 4: # if optimal location is X+h_l
                chosen_x = 0
                offset = offset+step[1]
                obj_val[0,II+1] = obj_val[2,II]
                comp_main.setOffset(CH,offset-step[0])
                obj_val[1,II+1] = objective_fun(opm_main)
                obj_val[2,II+1] = obj_val[4,II]
                comp_main.setOffset(CH,offset+step[0])
                obj_val[3,II+1] = objective_fun(opm_main)
                comp_main.setOffset(CH,offset+step[1])
                obj_val[4,II+1] = objective_fun(opm_main)

            case _:
                print('something went wrong: check your code fool!')
        II += 1
    print(f'Objective value per stage:\n {obj_val}')
    print(f'Steps taken: {step_taken}')

def optimize_search_neighbourhood(baseline,CH=0,rms=True,verbose=True):
    rescale_step = np.array([1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1])*1
    offset = baseline[CH]
    II = 6
    walkway = [offset]
    limit = -0.01
    the_same = 0
    obj_val = np.empty(3,float) 
    steps = np.array([-1,0,1])*rescale_step[CH]
    while II > 0:
        for idx, step in enumerate(steps):
            comp_main.setOffset(CH,offset+step,verbose=verbose)
            if not rms:
                obj_val[idx] = (objective_var(opm_main,verbose=verbose)**2).sum()
            else: 
                obj_val[idx] = (objective_RMS(opm_main,verbose=verbose)**2).sum() 
        obj_val = (obj_val-obj_val[1])/obj_val[1] # relative change
        if verbose:
            print(obj_val)
        # valid_idx = np.where(obj_val >= limit)[0]
        # best = valid_idx[obj_val[valid_idx].argmin()]
        best = np.argmin(obj_val)
        if best == 1:
            if the_same == 1:
                if verbose:
                    print(walkway)
                break
            else:
                the_same = 1
            if verbose:
                print('You where the chosen One!')
            steps *= 0.5
            # break
        else:
            offset += steps[best]
            the_same = 0
            if any(walkway==offset):
                if verbose:
                    print("You've been here before too")
                    print(walkway)
                break
            else:
                walkway.append(offset)
            if verbose:
                print(f'New offset: {offset}')
        
        II -= 1
    comp_main.setOffset(CH,offset,verbose=verbose)
    # opm_main.coarse_zero_sensors(verbose=verbose)
    if not rms:
        objective_var(opm_main,True)
    else:
        objective_RMS(opm_main,True,verbose=verbose)
    return offset
  
def lsq_compensation(baseline):
    rescale_step = [1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1]
    coils = [{'data': np.empty((16*3,2),float), 
              'field': np.array([baseline[i],baseline[i]+rescale_step[i]]),
              'optim': np.empty(1,float)} for i in range(8)]
    for idx, coil in enumerate(coils):
        coil['data'][:,0] = np.nan_to_num(np.ravel(opm_main.get_fields()))

        comp_main.setOffset(idx,coil['field'][1])
        opm_main.fine_zero_sensors()
        coil['data'][:,1] = np.nan_to_num(np.ravel(opm_main.get_fields()))

        slope = (coil['data'][:,1] - coil['data'][:,0])/(coil['field'][1] - coil['field'][0])
        intercept = coil['data'][:,0] - slope*coil['field'][0]
        coil['optim'] = np.linalg.lstsq(np.concatenate((slope[:,np.newaxis],np.zeros((48,2))),axis=1),
                                       -intercept,rcond=1)[0][0]
        # print(coil['optim'])
        comp_main.setOffset(idx,coil['optim'])
        opm_main.fine_zero_sensors()

    # for idx, coil in enumerate(coils):
    #     coil['data'][:,0] = np.nan_to_num(np.ravel(opm_main.get_fields()))

    # for idx, coil in enumerate(coils):
    #     comp_main.setOffset(idx,coil['field'][1])
    #     opm_main.fine_zero_sensors()
    #     coil['data'][:,1] = np.nan_to_num(np.ravel(opm_main.get_fields()))

    # for idx, coil in enumerate(coils):
    #     slope = (coil['data'][:,1] - coil['data'][:,0])/(coil['field'][1] - coil['field'][0])
    #     intercept = coil['data'][:,0] - slope*coil['field'][0]
    #     coil['optim'] = np.linalg.lstsq(np.concatenate((slope[:,np.newaxis],np.zeros((48,2))),axis=1),
    #                                    -intercept,rcond=1)[0][0]
    #     # print(coil['optim'])
    #     comp_main.setOffset(idx,coil['optim'])
    #     opm_main.fine_zero_sensors()

    # field_nm = ["x","y","z"]
    return coils
                    


##-- Actual online executions --##
def RMS_check_all(tmp_baseline,save=True):
        DATA = {i: {'offset': [], 'objVal': []} for i in range(8)}
        for ch in range(8):
            tmp_field, tmp_obj = check_optimize_one(opm_main,comp_main,tmp_baseline,CH=ch,rms=True)
            tmp_baseline[ch] = tmp_field[np.argmin(tmp_obj)]
            comp_main.setOffset(ch,tmp_baseline[ch]) # set to optimal
            opm_main.fine_zero_sensors()
            DATA[ch]['offset'] = tmp_field
            DATA[ch]['objVal'] = tmp_obj
        print(tmp_baseline)
        dt_string = datetime.now().strftime("%d-%m-%Y_%H:%M:%S") # dd/mm/YY H:M:S
        if save:
            np.savez('RMS_fieldOffset_optimize_all '+dt_string,data=DATA,baseline=tmp_baseline)
        return tmp_baseline

def RMS_check_xyz(tmp_baseline,way=["z","y","x"],save=True):
        check_optimize_one(opm_main,comp_main,tmp_baseline,CH=0,rms=True,direction='z')
        objective_RMS(opm_main,True)
        DATA = {i:{j:{'offset':[], 'objVal':[]} for j in range(3)} for i in way}
        for i in way:
            for ch in range(3):
                DATA[i][ch]['offset'], DATA[i][ch]['objVal'] = check_optimize_one(opm_main,comp_main,tmp_baseline,CH=ch,rms=True,direction=i)
                objective_RMS(opm_main,True)
        dt_string = datetime.now().strftime("%d-%m-%Y_%H:%M:%S") # dd/mm/YY H:M:S
        if save:
            np.savez('RMS_fieldOffset_exploration '+dt_string,DATA=DATA)

def collect_fields_raw(baseline,II=10):
    rescale_step = [1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1]
    step_size = 1

    for ch in range(8):
        DATA = np.empty((16,3,II+1),float)
        steps = np.arange(-step_size*(II/2),step_size*(II/2)+step_size,step_size)*rescale_step[ch]
        for idx, step in enumerate(steps):
            comp_main.setOffset(ch,baseline[ch]+step)
            if idx == 0:
                opm_main.coarse_zero_sensors()
                opm_main.fine_zero_sensors()
            else:
                opm_main.fine_zero_sensors()
            DATA[:,:,idx] = opm_main.get_fields()
        dt_string = datetime.now().strftime("%d-%m-%Y")
        np.savez('compensationField_'+ch_names[ch].replace('/',':')+' '+dt_string,data=DATA,field=baseline[ch]+steps)
        comp_main.setOffset(ch,baseline[ch])

    
def callibrate_fields(baseline,II,rms=True,verbose=True):
    new_field = baseline
    with Bar('Processing...') as bar:
        for i in range(II):
            for ch in range(8):
                new_field[ch] = optimize_search_neighbourhood(baseline,CH=ch,rms=rms,verbose=verbose)
                bar.next(100/(8*II))
    return new_field


def print_sensor_fields():
    sensorDict = service.data_source.hardware_state._sensors
    for chassis_id, sensors in sensorDict.items():
        for s in sensors:
            print(f'{s.chassis_id} {s.sensor_id} {s.fields}')

# note: when OPMs are facing the projector
# Y compensation is equal to z for OPMs
# Z compensation is equal to x for OPMs
# X compensation is equal to y for OPMs 

##------------------------------##
## Ready for data collection
# baseline = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])   # all zero
# baseline = np.array([56.8, 62.2, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0])   # fieldtuning from fluxgate (24/08/2023? what is this date JACOB?) 
# baseline = np.array([49.7, 47.2, 0.5, 0.2, -0.2, -0.2, 0.0, 0.0])   # fieldtuning through OPMs (18/07/2023) 
# baseline = np.array([46.3, 37.2, 27.3,  0.5,  2.5, -0.5, -2.5, -2.5]) # check_optimize_one findings based on mean x/y/z RMS
# baseline = np.array([48.0, 50.0, -0.8, -0.1, -0.4, -0.3, 0.2, -0.1])   # fieldtuning with all gradient (18/07/2023) (very low RMS values)
# baseline = np.array([51.5, 52.0, -2.8, -0.5, -0.6, -0.125, 0.2, 0.0])   # after calibration algorithm rep=2 (19/07/2023)
# baseline = np.array([51.875, 52.0, -1.8, -0.55, -0.7, -0.075, 0.15, 0.0])   # after movement of sensors  (19/07/2023)
# baseline = np.array([52.625, 54.000,-1.800, -0.700, -0.800, 0.200, 0.175, -0.0125])   # after calibration rep=3 (19/07/2023)
# baseline = np.array([5.2125e+01,  5.4750e+01, -1.8000e+00, -7.5000e-01, -9.0000e-01,  2.5000e-01, 1.2500e-01, -1.2500e-02])   # after calibration without bad channels(19/07/2023)
# baseline = np.array([5.4875e+01, 5.6000e+01, -3.3000e+00, -7.5000e-01, -8.0000e-01, 3.0000e-01, 1.7500e-01, -1.2500e-02]) # callibration rep=2 (20/07/2023)
# baseline = np.array([53.875, 58.5, -2.05, -0.85, -0.9, 0.4, 0.125, 0.0875]) # callibration after movement(20/07/2023)
# baseline = np.array([52.375, 64.5, -2.05, -0.25, -1.5, -0.2, 0.225, -0.1125]) # heartbeat trial (cal. cycle 1) (20/07/2023)
# baseline = np.array([54.125, 68.5, -2.05, -0.05, -1.05, 0.3, 0.075, -0.0125]) # heartbeat trial (cal. cycle 2) (20/07/2023)
# baseline = np.array([53.75803086108896, 56.016716053628386, -3.227057313520095, -0.6241844076352602, -1.305059036875172, -0.2643347156506543, 0.2385904264529274, -0.06815716818364435]) # lsq sol (21/07/2023)
baseline = np.array([57.5, 106.9, 3.2, 0.0, 0.0, 0.0, 0.0, 0.0])
# baseline = np.array([43.0650743264927, 106.80433361839286, 8.330305990304389, -0.5384767654016566, -1.4624488268245388, -0.06682680108122521, 0.5934237633265012, -0.010551713450945573])



need_setup = False
# initiate classes for both APIs
try:
    with  FieldLineService(ip_list) as service:
        opm_main = opm_fieldline_control()
        comp_main = comp_field_control()
        reset_baseline(comp_main,baseline)
        # opm_main.restart_sensors()
        opm_main.coarse_zero_sensors()
        opm_main.fine_zero_sensors()
        objective_RMS(opm_main,True)
        if need_setup:
            try:
                if any([service.get_sensor_state(0,ch+1) == None for ch in range(16)]):
                    opm_main.coarse_zero_sensors()
                if all([service.get_sensor_state(0,ch+1).name == 'SENSOR_READY' for ch in range(16)]):
                    opm_main.restart_sensors()
                if any([service.get_sensor_state(0,ch+1).name == 'SENSOR_RESTARTED' for ch in range(16)]):
                    opm_main.coarse_zero_sensors()
                if any([service.get_sensor_state(0,ch+1).name == 'SENSOR_COARSE_ZEROED' for ch in range(16)]):
                    opm_main.fine_zero_sensors()
                if any([service.get_sensor_state(0,ch+1).name == 'SENSOR_FINE_ZEROED' for ch in range(16)]):
                    print('Sensors are ready to go!')
                    # objective_RMS(opm_main,True)
                    objective_var(opm_main,True)
            except:
                print('sensors state is fucked?')

        # opm_main.get_fields()
        # opm_main.fine_zero_sensors()
        # time.sleep(5)
        # comp_main.setOffset(0,baseline[0]+2)
        # opm_main.fine_zero_sensors()
        # time.sleep(5)
        # objective_RMS(opm_main,True)

        mid_time = time.time()
        print(f'preable execution time: {mid_time-start_time}s')
        tmp_baseline = baseline # set temporary baseline vals
        # opm_main.get_fields()

        # Optimization content goes here!!
        # RMS_check_xyz(tmp_baseline)
        # tmp_baseline = RMS_check_all(tmp_baseline)
        # twosided_check_optimize_one(opm_main,comp_main,tmp_baseline,CH=0,objective_fun=obj_tmp)
        
        res = lsq_compensation(tmp_baseline)
        new_baseline = [coil['optim'] for coil in res]
        print(new_baseline)
        np.savez('optim_set',data=res)
        objective_RMS(opm_main,True)

        # optimize_search_neighbourhood(tmp_baseline,CH=0,rms=False)
        # for i in range(1):
        #     new_field = callibrate_fields(tmp_baseline,II=1,rms=True,verbose=True)
        #     print(new_field)
        # objective_RMS(opm_main,True)


        # comp_main.setOffset(0,baseline[0]+1,delay=0.1)
        # obj_val = (objective_var(opm_main,True)**2).sum()
        # print(obj_val)

        # service.open() # for some reason you need to reopen service eventhough it was opened at the with as statement?
        # opm_main.test_RT_data()

        # collect_fields_raw(tmp_baseline)
        # END of optimization   
        comp_main.ser_monitor.join()
        end_time = time.time()
        print(f'Optimization execution time: {end_time-mid_time}s')
        print(f'total execution time: {end_time-start_time}s')
except ConnectionError as e:
    logging.error("Failed to connect: %s" % str(e))



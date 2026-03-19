import numpy as np
from scipy.optimize import nnls
import scipy as scp
import time
import os
# baseline = np.array([50,100,5,0,0,0,0,0])
# np.savez('last_baseline',optim_baseline=baseline)

with np.load("last_baseline.npz") as file:
    new_baseline = file['optim_baseline']
print(new_baseline)
# with open("my_file.txt","w") as file:
    # file.write(([1,2,3,4,5,6,7,8]))

# with open("my_file.txt","r") as file:
    # print(np.array(file.read()))

qq = np.load("dynamic_optimizer-1.npz",allow_pickle=True)
print(qq['DATA'].shape)

qq['DATA']['data_frames']

##--
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
    print(scp.linalg.svd(Lvec,compute_uv=False))
    new_baseline, residuals = nnls(np.transpose(Lvec),-offsets)
    print(residuals)
    return new_baseline
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
raw_array = np.load('data/optimizing_data_11-1.npz')
data_array = raw_array['data_array']
base_array = raw_array['base_array']

# print(np.append(base_array[3:,3:-1],np.ones((6,1)),axis=1))
# print(data_array[:,:,3:].shape)


new_baseline = nonneg_double_lsq_algorithm(base_array,data_array,16)
print(new_baseline)
# new_baseline[:3] = homo_field_solver(base_array,data_array,16)
# print(new_baseline)
# new_baseline[3:] = grad_field_solver(base_array,data_array,16)
# print(new_baseline)

print(scp.linalg.svd(data_array.reshape(3*16,9),compute_uv=False)) # maybe there is a solution to find here?



##--


# time.sleep(20)
# duration = 1  # seconds
# freq = 440  # Hz
# os.system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
# os.system('spd-say "your program has finished"')


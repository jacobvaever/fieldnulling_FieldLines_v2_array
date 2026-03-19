##-- analysis of compensations fields --##
import numpy as np
import matplotlib.pyplot as plt

# coils_nm = ["Y","Z","X"]
coils_nm = ["Y","Z","X","dBy:dy","dBz:dy","dBz:dz","dBz:dx","dBy:dx"]
coils = []
fig, ax = plt.subplots(8,1)
for i, coil in enumerate(coils_nm):
    ## reading data from compressed numpyt files ##
    data  = np.load('compensationField_'+coil+' 19-07-2023.npz')
    coils.append(data)
    fields = data['data']
    steps  = data['field']
    # print(fields)
    # print(steps)
    '''
    fig, ax = plt.subplots(4,4)
    # print()
    XX = np.nanmean(fields,axis=1)
    # L2 = np.sqrt(np.nansum(XX**2, axis=0))
    # XX_L2 = XX/L2[np.newaxis,:]
    i = 0
    for x in range(0,4):
            for y in range(0,4):
                ax[x,y].set(title='Channel '+str(i+1))
                ax[x,y].plot(steps, XX[i,:], linewidth=2.0)
                i += 1
    plt.show()

    '''
    
    XX = np.nanmean(np.nanmean(np.sqrt(fields**2), axis=1), axis=0)
    ax[i].plot(steps,XX), ax[i].set(title=coil, xlim=(steps[0],steps[len(steps)-1]))
    ax[i].grid()
# plt.show()


field_nm = ["x","y","z"]
# coil_optimal = np.empty()
for coil in coils:
    slope = (coil['data'][:,:,-1] - coil['data'][:,:,0])/(coil['field'][-1] - coil['field'][0])
    slope = np.nan_to_num(slope)
    # print(slope.shape)
    intercept = coil['data'][:,:,0] - slope*coil['field'][0]
    intercept = np.nan_to_num(intercept)
    # print(intercept.shape)
    intercept_validate = coil['data'][:,:,-1] - slope*coil['field'][-1]
    # print(np.concatenate((np.reshape(slope,(-1,1)),np.zeros((48,1)),np.zeros((48,1))),axis=1).shape)
    coil_optimal = np.linalg.lstsq(np.concatenate((np.reshape(slope,(-1,1)),np.zeros((48,1)),np.zeros((48,1))),axis=1),-np.ravel(intercept),rcond=1)[0]
    print(coil_optimal[0])
    for idx, nm in enumerate(field_nm):
        print(f'RMS of {nm}: {np.sqrt(((np.dot(slope,coil_optimal[0]) + intercept)[:,idx]**2).mean())}')
    # prediction = norm

###############################################
##--         All gradients at once         --##
slope = np.empty((48,8),float)
intercept = np.empty((48,8),float)
y1 = np.array([np.nan_to_num(np.ravel(coil['data'][:,:, 0])) for coil in coils])
y2 = np.array([np.nan_to_num(np.ravel(coil['data'][:,:,-1])) for coil in coils])
x1 = np.array([np.nan_to_num(coil['field'][ 0]) for coil in coils])
x2 = np.array([np.nan_to_num(coil['field'][-1]) for coil in coils])

for idx, coil in enumerate(coils):
    slope[:,idx] = (np.nan_to_num(np.ravel(coil['data'][:,:,-1])) - np.nan_to_num(np.ravel(coil['data'][:,:,0])))/(np.nan_to_num(np.ravel(coil['field'][-1])) - np.nan_to_num(np.ravel(coil['field'][0])))

###############################################
##--         Finite element method         --##

# fig, ax = plt.subplots(8,1)
for idx, coil in enumerate(coils):
    # print(all((np.nan_to_num(coil['data']).reshape(-1,11))[:,0]==np.ravel(np.nan_to_num(coil['data'][:,:,1]))))
    tmp = np.diff(np.nan_to_num(coil['data']),axis=2).reshape(-1,10)/np.diff(coil['field'])
    # ax[idx].plot(coil['field'][0:-1],tmp[0,:])
    # print(np.min(np.abs(tmp),axis=1))
    # print(coil['field'][np.argmin(np.abs(tmp),axis=1)])
    # print(np.linalg.lstsq(tmp, ))
# plt.show()





###############################################

###############################################
baseline = np.array([51.875, 52.0, -1.8, -0.55, -0.7, -0.075, 0.15, 0.0]) 
V = np.array([[baseline[2],-(baseline[3]+baseline[5]),baseline[7],baseline[6]],
              [x1[0],baseline[7],baseline[3],baseline[4]],
              [baseline[1],baseline[6],baseline[4],baseline[5]]])
V_alt = np.array([[-(baseline[3]+baseline[5]),baseline[7],baseline[6]],
              [baseline[7],baseline[3],baseline[4]],
              [baseline[6],baseline[4],baseline[5]]])
print(V.shape)
tmp_y = np.nan_to_num(coils[0]['data'][:,:,0])
print(tmp_y.shape)

B = np.linalg.lstsq(V_alt,tmp_y.transpose())[0].mean(axis=1)
# B = np.linalg.lstsq(V_alt,(tmp_y+np.array([x1[0],baseline[1],baseline[2]])).transpose())[0].mean(axis=1)
B = np.insert(B,0,1)
print(B)

A = np.array([[0, 0, 1, -B[1], 0, -B[1], B[3], B[2]],
             [1, 0, 0, B[2], B[3], 0, 0, B[1]],
             [0, 1, 0, 0, B[2], B[3], B[1], 0]])
G = np.linalg.lstsq(A,tmp_y.transpose())[0].mean(axis=1)
print(G)

print(tmp_y.ravel()[0:3]==tmp_y[0,:])
print(tmp_y[0,:])


# print()
###############################################

# # baseline = np.array([51.875, 52.0, -1.8, -0.55, -0.7, -0.075, 0.15, 0.0])  # baseline at 19/07/2023 data recording (surely)
# baseline = np.empty(8,float)
# for idx, coil in enumerate(coils):
#     baseline[idx] = coil['field'][6]
# # print(baseline)
# # system_a = np.repeat(baseline[:,np.newaxis],11,axis=1)
# system_a = np.repeat(baseline[0:3,np.newaxis],11,axis=1)
# # for idx, coil in enumerate(coils):
# system_a[0,:] = coils[0]['field']
# # print(system_a)
# system_b = np.nanmean(coils[0]['data'],axis=0)
# # print(system_b)

# system_x = np.linalg.lstsq(system_a.transpose(),system_b.transpose(),rcond=1)
# print(system_x[0].shape)
# print(system_x)

# print(system_b.transpose()-np.dot(system_a.transpose(),system_x[0]))

# print(np.dot(system_a.transpose(),system_x[0]))
# print(system_b.transpose())

# field_nm = ["x","y","z"]
# for coil in coils:
#     slope = (coil['fields'][:,:,-1] - coil['fields'][:,:,0])/(coil['compensations'][-1] - coil['compensations'][0])
#     slope = np.nan_to_num(slope)
#     intercept = coil['fields'][:,:,0] - slope*coil['compensations'][0]
#     intercept = np.nan_to_num(intercept)
#     intercept_validate = coil['fields'][:,:,-1] - slope*coil['compensations'][-1]
#     coil_optimal = np.linalg.lstsq(slope,intercept,rcond=1)
#     print(coil_optimal[0])
#     for idx, nm in enumerate(field_nm):
#         print(f'RMS of {nm}: {np.sqrt(((np.dot(slope,coil_optimal[0]) + intercept)[:,idx]**2).mean())}')
#     # prediction = norm


aseline[7],baseline[3],baseline[4]],
              [baselin
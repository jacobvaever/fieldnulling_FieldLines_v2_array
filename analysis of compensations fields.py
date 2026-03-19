##-- analysis of compensations fields --##
import numpy as np
import matplotlib.pyplot as plt

coils_nm = ["By","Bz","Bx"]
# coils_dt = {nm: np.empty((16,3,21),float) for nm in coils_nm}
coils = []
fig, ax = plt.subplots(3,1)
for i, coil in enumerate(coils_nm):
    ## reading data from compressed numpyt files ##
    data   = np.load('data/compensationField_test_'+coil+'.npz')
    coils.append(data)
    fields = data['fields']
    steps  = data['compensations']
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
for coil in coils:
    slope = (coil['fields'][:,:,-1] - coil['fields'][:,:,0])/(coil['compensations'][-1] - coil['compensations'][0])
    slope = np.nan_to_num(slope)
    # print(slope.shape)
    intercept = coil['fields'][:,:,0] - slope*coil['compensations'][0]
    intercept = np.nan_to_num(intercept)
    # print(intercept.shape)
    intercept_validate = coil['fields'][:,:,-1] - slope*coil['compensations'][-1]
    coil_optimal = np.linalg.lstsq(slope,intercept,rcond=1)
    print(coil_optimal[0])
    # for idx, nm in enumerate(field_nm):
    #     print(f'RMS of {nm}: {np.sqrt(((np.dot(slope,coil_optimal[0]) + intercept)[:,idx]**2).mean())}')
    # prediction = norm

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



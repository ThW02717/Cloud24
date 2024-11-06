import numpy as np
from plottools import dataPlotters
import matplotlib.pyplot as plt

# TODO 1: import your vvmtools
from vvmtool import VVMTools

# TODO 2: change the expname to your experiment name
# prepare expname and data coordinate
expname  = 'Urban+Grass, Sounding 1'
nx = 128; x = np.arange(nx)*0.2
ny = 128; y = np.arange(ny)*0.2
nz = 50;  z = np.arange(nz)*0.04
nt = 721; t = np.arange(nt)*np.timedelta64(2,'m')+np.datetime64('2024-01-01 05:00:00')

# TODO 3: change the data to your data (seven lines for BL height and one shading for w'th')
# read or create data
t_range = np.arange(0, 721)
domain_u = (None, None, None, None, 0, 64)
domain_g = (None, None, None, None, 64, 128)
domain_all = (None, None, None, None, None, None)

domain_range = domain_all
vvm = VVMTools("/data/mlcloud/pike/VVM/DATA/5_1hetero")


bl_point5 = vvm.func_time_parallel(vvm.blPointfive, t_range, domain_range=domain_range)
bl_tke=vvm.blOther('TKE', 0.3, t_range, domain_range = domain_range)
bl_ens=vvm.blOther('ENS', 3e-5, t_range, domain_range = domain_range)
bl_grad=vvm.func_time_parallel(vvm.blGrad, t_range, domain_range = domain_range)
bl_wthp, bl_wthm, bl_wthn = vvm.find_wth_boundary(t_range, 0.001, domain_range = domain_range)

WTH = vvm.func_time_parallel(vvm.cal_WTH, t_range, domain_range = domain_range)
WTH = np.swapaxes(WTH, 0, 1)

# TODO 4: change the figpath to your figure path
# create dataPlotter class
figpath           = '.'
data_domain       = {'x':x, 'y':y, 'z':z, 't':t}
data_domain_units = {'x':'km', 'y':'km', 'z':'km', 't':'LocalTime'}
dplot = dataPlotters(expname, figpath, data_domain, data_domain_units)

# draw z-t diagram
# input data dimension is (nz, nt)
# [output] figure, axis, colorbar axis

# TODO 5: change the levels to your data range, 
#         add pblh_dicts for your seven lines, 
#         change the title_left and title_right,
#         change figname for output file name.
fig, ax, cax = dplot.draw_zt(data=WTH, 
                             levels=np.arange(-0.04, 0.041, 0.005), 
                             extend='both', 
                             pblh_dicts={r'$\theta$ + 0.5 K': bl_point5,
                                         r'max d$\theta$/dz ': bl_grad,
                                         r'TKE': bl_tke,
                                         r'Enstrophy': bl_ens,
                                         r'top($\overline{w^\prime \theta^\prime}$ + )': bl_wthp,
                                         r'min($\overline{w^\prime \theta^\prime}$)': bl_wthm,
                                         r'top($\overline{w^\prime \theta^\prime}$ - )': bl_wthn,
                                        },
                             title_left=r'Vertical $\theta$ transport', 
                             title_right=f'Domain: All', 
                             figname='S1_all.png', 
                      )


plt.show()

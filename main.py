import vvmtool
import plottools
import importlib
importlib.reload(vvmtool)
VVMTools = vvmtool.VVMTools
importlib.reload(plottools)
VVMPlots = plottools.VVMPlot

vvm = VVMTools(case_path='/data/mlcloud/pike/VVM/DATA/5_1hetero')
plotter = VVMPlots()
plotter.plot_bl(vvm, t_range=list(range(0, 480)), domain_range=plotter.domain_grass, folder_path='/data/mlcloud/pike/data/HW7',sounding_name='1')



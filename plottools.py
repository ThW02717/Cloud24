import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm

class VVMPlot:
    def __init__(self, fontsize=12, figsize=(6, 4), cmap='RdBu_r'):
        """
        Initialize the VVMPlot class.

        Parameters
        ----------
        fontsize : int, optional
            The font size for plot titles and labels (default is 12).
        figsize : tuple, optional
            The figure size of the plot (default is (6, 4)).
        cmap : str, optional
            The colormap for contour plots (default is 'RdBu_r').
        """
        self.fontsize = fontsize
        self.figsize = figsize
        self.cmap = cmap

    def _plot_contour(self, data, zc, title, path=None, levels=None):
        """
        Internal method for plotting contour and shading.
        """
        print("Data shape:", data.shape)  # Check the shape of the data
        plt.figure(figsize=self.figsize)
        if levels is None:
            levels = np.linspace(np.nanmin(data), np.nanmax(data), 50)
        plt.contourf(data, levels=levels, cmap=self.cmap, extend='both')
        plt.colorbar(label=title)
        plt.xlabel("Time", fontsize=self.fontsize)
        plt.ylabel("Height (m)", fontsize=self.fontsize)
        plt.title(title, fontsize=self.fontsize)
        if path:
            plt.savefig(path, dpi=200)
        plt.show()

    def plot_bl(self, vvm_tools, t_range, domain_range, save_path=None):
        """
        Plots the five boundary layer height methods from the VVMTools class.

        Parameters
        ----------
        vvm_tools : VVMTools
            An instance of the VVMTools class used to retrieve data.
        t_range : list
            A list of time indices for the plot.
        domain_range : tuple
            A tuple specifying the domain range in VVMTools.
        save_path : str, optional
            File path to save the figure.
        """
        zc = vvm_tools.get_var('zc', 0, numpy=True)

        # Get boundary layer heights using different methods
        bl_grad = vvm_tools.func_time_parallel(vvm_tools.blGrad, t_range, domain_range=domain_range, cores=5)
        print("bl_grad shape:", bl_grad.shape)
        bl_pointfive = vvm_tools.func_time_parallel(vvm_tools.blPointfive, t_range, domain_range=domain_range, cores=5)
        bl_tke = vvm_tools.blOther('TKE', 0.3, t_range, domain_range=domain_range)
        bl_ens = vvm_tools.blOther('ENS', 3e-5, t_range, domain_range=domain_range)
        bl_wth = vvm_tools.blOther('WTH', 0.01, t_range, domain_range=domain_range)

        bl_data = {
            'PBL Grad Method': bl_grad,
            'PBL Theta+0.5 Method': bl_pointfive,
            'PBL TKE': bl_tke,
            'PBL ENS': bl_ens,
            'PBL WTH': bl_wth
        }

        for method, data in bl_data.items():
            self._plot_contour(data, zc, method, path=save_path)

    def TKE_t_z(self, TKE_data, fontsize=None, figsize=None, cmap=None, levels=None, path=None):
        """
        Plots the TKE evolution according to height.

        Parameters
        ----------
        TKE_data : 2D-ndarray
            A 2D map for TKE mean in x-y dimension.
        fontsize : int, optional
            The font size for plot titles and labels (overrides the class-level fontsize).
        figsize : tuple, optional
            The figure size of the plot (overrides the class-level figsize).
        cmap : str, optional
            The colormap for the plot (overrides the class-level colormap).
        levels : list, optional
            Contour levels for the plot.
        path : str, optional
            File path to save the plot.
        """
        fontsize = fontsize or self.fontsize
        figsize = figsize or self.figsize
        cmap = cmap or self.cmap

        plt.figure(figsize=figsize)
        if levels is None:
            levels = np.linspace(np.nanmin(TKE_data), np.nanmax(TKE_data), 50)
        plt.contourf(TKE_data, levels=levels, cmap=cmap, extend='both')
        plt.colorbar(label='TKE')
        plt.title('TKE Evolution with Height', fontsize=fontsize)
        plt.xlabel('Time', fontsize=fontsize)
        plt.ylabel('Height (m)', fontsize=fontsize)
        if path:
            plt.savefig(path, dpi=200)
        plt.show()


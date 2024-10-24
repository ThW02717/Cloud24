import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as colors

class VVMPlot:
    def __init__(self, fontsize=12, figsize=(6, 4), cmap='RdBu_r'):
        self.fontsize = fontsize
        self.figsize = figsize
        self.cmap = cmap
        self.domain_urban = (None, None, None, None, 0, 64)    # domain_range=plotter.domain_urban
        self.domain_grass = (None, None, None, None, 64, 128)  # domain_range=plotter.domain_grass
        self.domain_all = (None, None, None, None, None, None)

    def _plot_contour_with_lines(self, T, Z, contourf_data, lines_data, clev, tick, lab, title, r_title, folder_path=None, image_nickname=None):
        """
        A combined contour and line plot for boundary layer data and WTH.
        """
        plt.figure(figsize=(10, 6))
        edge_value = max(-np.nanmin(contourf_data), np.nanmax(contourf_data))
        plt.contourf(T, Z, contourf_data, cmap='bwr', levels=clev, extend='both')
        cbar = plt.colorbar(label=r'$\overline{w^\prime \theta^\prime}$ [K m/s]')
        
        for label, data in lines_data.items():
            plt.plot(T[0], data, label=label)

        plt.legend(fontsize=12, loc='upper left')
        plt.xlabel('Local Time')
        plt.ylabel('Height [m]')
        plt.grid(linestyle="dashed", linewidth=0.5)
        plt.tick_params(right=True, top=True)        
        plt.xticks(tick, lab)
        plt.title(title, fontproperties={'size':16, 'weight': 'bold'}, loc='left')
        plt.title(r_title, fontproperties={'size':14}, loc='right')        
        plt.legend()
        plt.tight_layout()
        if folder_path:
            plt.savefig(f'{folder_path}/{image_nickname}.png', dpi=300)

    def plot_bl(self, vvm_tools, t_range, domain_range=None, folder_path=None, sounding_name=None):
        zc = vvm_tools.get_var('zc', 0, numpy=True)
        if domain_range == 'all':
            domain_range = self.domain_all
            right_title = f'Domain: All, Sounding: #{sounding_name}'
            image_nickname = f'PBLH_S{sounding_name}_All'
        elif domain_range == 'urban':
            domain_range = self.domain_urban
            right_title = f'Domain: Urban, Sounding: #{sounding_name}'            
            image_nickname = f'PBLH_S{sounding_name}_Urban'
        elif domain_range == 'grass':
            domain_range = self.domain_grass
            right_title = f'Domain: Grass, Sounding: #{sounding_name}'
            image_nickname = f'PBLH_S{sounding_name}_Grass'

        bl_grad = vvm_tools.func_time_parallel(vvm_tools.blGrad, t_range, domain_range=domain_range)
        bl_pointfive = vvm_tools.func_time_parallel(vvm_tools.blPointfive, t_range, domain_range=domain_range)
        bl_tke = vvm_tools.blOther('TKE', 0.3, t_range, domain_range=domain_range)
        bl_ens = vvm_tools.blOther('ENS', 3e-5, t_range, domain_range=domain_range)
        bl_wth = vvm_tools.blOther('WTH', 0.01, t_range, domain_range=domain_range)
        WTH = vvm_tools.func_time_parallel(vvm_tools.cal_WTH, t_range, domain_range=domain_range)
        WTH = np.swapaxes(WTH, 0, 1)

        T, Z = np.meshgrid(t_range, zc)

        tick = np.arange(0, len(t_range)+1, 30)
        lab = ['05', '06', '07', '08', '09', '10', '11', '12', '13'
               , '14', '15', '16', '17', '18', '19', '20', '21',
               '22', '23', '24', '01', '02', '03', '04', '05']
        lab = lab[:len(tick)]

        bl_data = {
            'TKE = 0.3 [m$^{2}$/s$^{2}$]': bl_tke,
            'ENS. = 3x10$^{-5}$ [1/s$^{2}$]': bl_ens,
            'WTH = 0.01 [K m/s]': bl_wth,
            'dθ/dz max': bl_grad,
            'θ$_{sfc}$ +0.5K': bl_pointfive
        }

        self._plot_contour_with_lines(T, Z, contourf_data=WTH, lines_data=bl_data, clev=np.arange(-0.123,0.124,0.006), tick=tick, lab=lab,
                                      title=r'Average $\overline{w^\prime \theta^\prime}$ & PBLH', r_title=right_title,
                                      folder_path=folder_path, image_nickname=image_nickname)

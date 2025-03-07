import pathlib
import os
import xarray as xr
import re
import numpy as np
import multiprocessing
import datetime
import logging
from scipy.ndimage import uniform_filter1d
class VVMTools:
    def __init__(self, case_path, debug_mode=False):
        self.CASEPATH = case_path
        self.DEBUGMODE = debug_mode

        self.VARTYPE = {}
        self.DIM = {}
        self.INIT = {}
        
        self._build_variable_type_dict()
        self._load_topo_variables()
        self._get_initial_profile()        
        self._get_date_time()
        self._build_dimension()

        if debug_mode:
            logging.basicConfig(level=logging.DEBUG)


    def _get_date_time(self):
        # Define start and end times
        start_time = datetime.datetime.strptime("05:00", "%H:%M")
        end_time = start_time + datetime.timedelta(days=1)  
        steps = 720
        time_delta = (end_time - start_time) / steps
        self.time_array_str = [(start_time + i * time_delta).strftime("%H:%M") for i in range(steps)]

    def _extract_file_info(self, filename):
        # Extract case name, variable type, and time information from the filename
        match = re.match(r'(\w+)\.[CL]\.(\w+)-(\d+)\.nc', filename)
        if match:
            case_name = match.group(1)
            variable_type = match.group(2)
            time_info = match.group(3)
            return case_name, variable_type, time_info
        return None, None, None

    def _record_variables_in_dict(self, file_path, variable_type):
        not_important_variables = {"time", "xc", "yc", "lon", "lat", "zc", "lev"}
        try:
            with xr.open_dataset(file_path) as ds:
                for variable in ds.variables:
                    if variable in self.VARTYPE:
                        if variable in not_important_variables:
                            continue
                        logging.warning(f"{variable} already exists in {self.VARTYPE[variable]}, renaming as {variable}_2 in {variable_type}.")
                        self.VARTYPE[f"{variable}_2"] = variable_type
                        
                    else:
                        # Add the variable and its type to the dictionary
                        self.VARTYPE[variable] = variable_type
                ds.close()
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")

    def _build_variable_type_dict(self):
        # Walk through the directory and find all .nc files with time 000000
        for root, dirs, files in os.walk(self.CASEPATH):
            for filename in files:
                if filename.endswith(".nc"):  # Search for all .nc files
                    case_name, variable_type, time_info = self._extract_file_info(filename)
                    if time_info == "000000":  # Only process files with time 000000
                        file_path = os.path.join(root, filename)
                        self._record_variables_in_dict(file_path, variable_type)

    def _build_dimension(self):
        # print(self.VARTYPE)
        self.DIM["xc"] = self.get_var("xc", 0).to_numpy()
        self.DIM["yc"] = self.get_var("yc", 0).to_numpy()
        self.DIM["zc"] = self.get_var("zc", 0).to_numpy()
        return

    def _load_topo_variables(self):
        """Load variables from the TOPO.nc file and add them to the VARTYPE dictionary."""
        topo_file = os.path.join(self.CASEPATH, 'TOPO.nc')
        if not os.path.exists(topo_file):
            logging.warning(f"TOPO.nc not found in {self.CASEPATH}")
            return

        try:
            with xr.open_dataset(topo_file) as ds:
                for variable in ds.variables:
                    self.VARTYPE[variable] = "TOPO"  # Label these variables as "TOPO"
        except Exception as e:
            logging.error(f"Error reading {topo_file}: {e}")

    def get_variable_file_type(self, variable_name):
        return self.VARTYPE.get(variable_name, "Variable not found")

    def _Range_tuple_check(self, Range):
        if not isinstance(Range, (tuple, list)) or len(Range) != 6:
            raise ValueError("Range must be a tuple or list with 6 elements (k1, k2, j1, j2, i1, i2).")

    # Read initial profile and save to self.INIT
    def _get_initial_profile(self):
        # Initialize an empty list to store the extracted data
        data_array = []
        
        # Open the file for reading
        with open(self.CASEPATH + "/fort.98", 'r') as file:  # Replace 'datafile.txt' with your actual file name
            reading_data = False
            flag = False
            for line in file:
                # Check for the start of the data section
                if re.match(r'^\s*K,\s*RHO\(K\)', line):
                    reading_data = True
                    flag = False
                    continue
        
                # Stop reading data when the next set of equal signs appears
                if reading_data and re.match(r'^\s*={5,}', line):  # Matches a line with 5 or more "="
                    continue
        
                # Read and process data lines after the header
                if reading_data:
                    if re.match(r'^\s*\d+\s+', line):  # Matches lines with data starting with a number
                        # Split the line into values
                        values = line.split()
                        # Convert values to appropriate types (float)
                        values = list(map(float, values))
                        # Append to the data array
                        data_array.append(values)

                if re.match(r'^\s*K,\s*UG\(K\)', line):
                    break

        data_array = np.array(data_array)
        self.INIT["RHO"] = data_array[:, 1]
        self.INIT["THBAR"] = data_array[:, 2]
        self.INIT["PBAR"] = data_array[:, 3]
        self.INIT["PIBAR"] = data_array[:, 4]
        self.INIT["QVBAR"] = data_array[:, 5]

    def get_var(self, 
                var, 
                time, 
                domain_range=(None, None, None, None, None, None), # (k1, k2, j1, j2, i1, i2)
                numpy=False, 
                compute_mean=False, 
                axis=None):
        
        # Find the file associated with the given variable and time
        self._Range_tuple_check(domain_range)
        
        variable_type = self.get_variable_file_type(var)
        if self.DEBUGMODE:
            print(f"Variable type: {variable_type}")
        if variable_type == "Variable not found":
            print(f"Variable {var} not found in the dataset.")
            return None
        

        if variable_type == "TOPO":
            # Special case for TOPO variables, always in TOPO.nc
            topo_file = os.path.join(self.CASEPATH, 'TOPO.nc')
            try:
                ds = xr.open_dataset(topo_file)
                if var in ds.variables:
                    variable_data = ds[var].copy()  # Get the variable data
                    ds.close()
                    return variable_data
                else:
                    ds.close()
            except Exception as e:
                print(f"Error reading {topo_file}: {e}")
                return None
        else:
            
            # Construct the expected filename pattern for the given variable and time
            file_pattern = f"{variable_type}-{'{:06d}'.format(time)}.nc"
            regex_pattern = f".*{file_pattern}$"  # Convert glob pattern to regex
            if self.DEBUGMODE:
                print(f"Regex Pattern: {regex_pattern}")


            # Search for the file in the case path
            for root, dirs, files in os.walk(self.CASEPATH):
                for filename in files:
                    if re.match(regex_pattern, filename):
                        if self.DEBUGMODE:
                            print(f"File found: {filename}")
                        # Uncomment the following block to open and read the file
                        file_path = os.path.join(root, filename)
                        try:
                            ds = xr.open_dataset(file_path)
                            if var == "eta_2":
                                var = "eta"
                            if var in ds.variables:
                                k1, k2, j1, j2, i1, i2 = domain_range

                                dims = len(ds[var].indexes)
                                if any(r is not None for r in domain_range):
                                    if dims == 4:
                                        variable_data = ds[var][0, k1:k2, j1:j2, i1:i2].copy()
                                    elif dims == 3:
                                        variable_data = ds[var][0, j1:j2, i1:i2].copy()
                                    else:
                                        print("Please check the variables dimension")
                                else:
                                    variable_data = ds[var].copy()  # Get the variable data
                                ds.close()

                                if numpy:
                                    data = np.squeeze(variable_data.to_numpy())

                                    if compute_mean and axis is not None:
                                        return np.mean(data, axis=axis)
                                    elif compute_mean:
                                        return np.mean(data)
                                    else:
                                        return data

                                
                                return variable_data
                            else:
                                ds.close()
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")
                            return None

        print(f"No file found for variable {var} at time {time}.")
        return None


    # Call self.get_var in parallel
    def get_var_parallel(self, 
                         var, 
                         time_steps, # array or list of time
                         domain_range=(None, None, None, None, None, None),  # (k1, k2, j1, j2, i1, i2)
                         compute_mean=False,
                         axis=None, # axis for mean. e.g. (0, 1)
                         cores=5):
        self._Range_tuple_check(domain_range)

        if type(time_steps) == np.ndarray:
            time_steps = time_steps.tolist()
        
        if not isinstance(time_steps, (list, tuple)):
            raise TypeError("time_steps must be a list or tuple of integers.")
        
        # Use multiprocessing to fetch variable data in parallel
        with multiprocessing.Pool(processes=cores) as pool:
            results = pool.starmap(self.get_var, [(var, time, domain_range, True, compute_mean, axis) for time in time_steps])
        
        # Combine and return the results
        return np.squeeze(np.array(results))


    # Given any time-related function (e.g. def A(t)), the function will be parallelized
    # Domain_range included
    def func_time_parallel(self, 
                           func,
                           time_steps=list(range(0, 720, 1)), 
                           domain_range=(None, None, None, None, None, None),  # (k1, k2, j1, j2, i1, i2)
                           cores=20):
        self._Range_tuple_check(domain_range)
        
        if type(time_steps) == np.ndarray:
            time_steps = time_steps.tolist()
            
        if not isinstance(time_steps, (list, tuple)):
            raise TypeError("time_steps must be a list or tuple of integers.")

        # Use multiprocessing to fetch variable data in parallel
        with multiprocessing.Pool(processes=cores) as pool:
            results = pool.starmap(func, [(time, domain_range) for time in time_steps])
        
        # Combine and return the results
        return np.squeeze(np.array(results))
    ###########################################################################################

    # 2D MAP Data of of specif Z in the X, Y domain 
    def horizontalMap (self, var, time , z):
        variable = self.get_var(var , time, domain_range=(z, z + 1, None, None, None, None), numpy=True)
        return variable
    # Vertical Profile data of specifc (x, y)
    def verticalPro (self, var, time ,x , y):
        variable = self.get_var(var , time, domain_range=(None, None, y, y + 1, x, x + 1), numpy=True)
        return variable
    # Cross Section data of specific y line
    def crossSection (self, var, time , y):
        variable = self.get_var(var , time, domain_range=(None, None, y, y+1, None, None), numpy=True)
        return variable

    ############################################################################################
    # TKE, ENS, Perturbation flux Domain Average
    def cal_TKE(self, t, domain_range=(None, None, None, None, None, None)):
        u = self.get_var("u", t, domain_range=domain_range, numpy=True)
        v = self.get_var("v", t, domain_range=domain_range, numpy=True)
        w = self.get_var("w", t, domain_range=domain_range, numpy=True)
        u_regrid = (u[:, :, 1:] + u[:, :, :-1])[1:, 1:, :] / 2
        v_regrid = (v[:, 1:, :] + v[:, :-1, :])[1:, :, 1:] / 2
        w_regrid = (w[1:, :, :] + w[:-1, :, :])[:, 1:, 1:] / 2
        TKE = u_regrid**2 + v_regrid**2 + w_regrid**2
        
        return np.nanmean(TKE, axis=(1,2))


    def cal_ENS(self, t, domain_range=(None, None, None, None, None, None)):
        xi = np.squeeze(self.get_var("xi", t, domain_range=domain_range).to_numpy())
        eta = np.squeeze(self.get_var("eta_2", t, domain_range=domain_range).to_numpy())
        if eta.shape != xi.shape:
            eta = np.squeeze(self.get_var("eta", t, domain_range=domain_range).to_numpy())
        zeta = np.squeeze(self.get_var("zeta", t, domain_range=domain_range).to_numpy())
        enstrophy = np.mean(xi** 2 + eta** 2 + zeta** 2, axis=(1, 2))
        return enstrophy
    
    def cal_WTH(self, t, domain_range=(None, None, None, None, None, None)):
        w = self.get_var('w', t, domain_range = domain_range, numpy=True)
        th = self.get_var('th', t, domain_range = domain_range, numpy=True)
        w_regrid = (w[1:]+w[:-1])/2
        w_mean = self.get_var('w', time=t, domain_range = domain_range, numpy=True, 
                              compute_mean=True, axis=(1, 2))[:, np.newaxis, np.newaxis]
        th_mean = self.get_var('th', time=t, domain_range = domain_range, numpy=True, 
                               compute_mean=True, axis=(1, 2))[:, np.newaxis, np.newaxis]
        w_prime = w - w_mean
        th_prime = th - th_mean
        w_th = np.nanmean(w_prime * th_prime, axis=(1, 2))
        return w_th
    
    ######################################################################################
    ## 7 Kinds of Boundary Layer Height  in T, Z domain
    # max dtheta/dz
    '''
        Threshold:
        TKE: 0.3
        ENS: 3e-5
        EX: blTKE=vvm.blOther('TKE', 0.3, t, domain_range = domain)
            blENS=vvm.blOther('ENS', 3e-5, t, domain_range = domain)
            blGrad=vvm.func_time_parallel(vvm.blGrad, t, domain_range = domain)
            blPointfive=vvm.func_time_parallel(vvm.blPointfive, t, domain_range = domain)
            wthp, wthm, wthn = vvm.find_wth_boundary(t, 0.001, domain_range = domain)
    '''
    def blGrad(self, t, domain_range = (None, None, None, None, None, None)):
        th = self.get_var('th', t, numpy=True, domain_range = domain_range, compute_mean = True, axis = (1, 2))
        zc = self.get_var('zc', t, numpy=True)
        dth = np.gradient(th)
        max_index = np.argmax(dth)
        pbl_depth = zc[max_index] / 1000
        return pbl_depth
    
    # thata[0]+0.5
    def blPointfive(self, t, domain_range = (None, None, None, None, None, None)):
        th = self.get_var('th', t, numpy=True, domain_range = domain_range, compute_mean = True, axis = (1,2))
        zc = self.get_var('zc', t, numpy=True)
        for i in range(50):
            if (th[i] >= th[0]+0.5).any():
                pbl_depth = zc[i]
                break
        return pbl_depth / 1000
    
    # TKE, ENS, WTH
    def blOther(self, var_name, threshold, t, domain_range=(None, None, None, None, None, None)):
        zc = self.get_var("zc", 0).to_numpy()
        if var_name == "TKE":
            var = self.func_time_parallel(self.cal_TKE, t, domain_range=domain_range, cores=20)
        elif var_name == "ENS":
            var = self.func_time_parallel(self.cal_ENS, t, domain_range=domain_range, cores=20)
        elif var_name == "WTH":
            var = self.func_time_parallel(self.cal_WTH, t, domain_range=domain_range, cores=20)
        else:
            raise ValueError(f"Unknown variable name: {var_name}")
        positive_mask = np.swapaxes(var, 0, 1) > threshold
        indices = np.argwhere(positive_mask)
        h = np.zeros(len(t))  
        for j_index, i_index in indices:
            if j_index + 1 < len(zc):
                h[i_index] = max(h[i_index], zc[j_index + 1])

        return h / 1000
    
    def find_wth_boundary(self, time_steps, threshold, domain_range = (None, None, None, None, None, None)):

        # Calculate WTH values across time steps and domain
        wth_values = self.func_time_parallel(self.cal_WTH, time_steps, domain_range = domain_range, cores=20)
        sign_array = np.sign(wth_values)  # Sign array for detecting boundaries
        height_levels = self.DIM['zc']
        
        # Initialize arrays for positive, min, and negative boundaries for each time step
        positive_boundary = np.full(len(time_steps), 0.0)
        min_boundary = np.full(len(time_steps), 0.0)
        negative_boundary = np.full(len(time_steps), 0.0)

        # Process each time step to identify boundaries based on threshold
        for i in range(len(time_steps)):
            wth_profile = wth_values[i]
            
            # Check if the maximum WTH value meets the threshold; if not, boundaries remain at 0
            if np.nanmax(wth_profile) >= threshold:
                # Detect positive-to-negative and negative-to-positive transitions in the sign array
                transition_points = np.diff(sign_array[i])

                # Positive boundary: First positive-to-negative transition
                pos_boundary_index = np.argmax(transition_points == -2) + 1
                positive_boundary[i] = height_levels[pos_boundary_index] / 1000 if pos_boundary_index > 0 else 0.0

                # Min boundary: Index of the minimum WTH value
                min_boundary_index = np.nanargmin(wth_profile)
                min_boundary[i] = height_levels[min_boundary_index] / 1000 if min_boundary_index > 0 else 0.0

                # Negative boundary: First negative-to-positive transition after min boundary
                neg_boundary_candidates = np.where(transition_points == 2)[0]
                neg_boundary_index = next((x + 1 for x in neg_boundary_candidates if x >= min_boundary_index), None)
                negative_boundary[i] = height_levels[neg_boundary_index] / 1000 if neg_boundary_index is not None else 0.0

                # Ensure the negative boundary is above the threshold, otherwise set it to 0
                if np.nanmax(wth_profile[min_boundary_index:]) < threshold:
                    negative_boundary[i] = 0.0
            else:
                # If max value doesn't reach the threshold, all boundaries stay at 0.0 (default)
                positive_boundary[i] = min_boundary[i] = negative_boundary[i] = 0.0

        return positive_boundary, min_boundary, negative_boundary
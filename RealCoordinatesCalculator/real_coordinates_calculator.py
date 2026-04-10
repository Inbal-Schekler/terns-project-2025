import os
import cv2
import json
import numpy as np
import pandas as pd
import configparser
from scipy.spatial.transform import Rotation as R

class RealCoordinatesCalculator:
    def __init__(self):
        # Load the configuration file
        config = configparser.ConfigParser()
        config_path = "/content/drive/MyDrive/tern_project/Eyal/RealCoordinatesCalculator/real_coordinates_calculator.ini"
        config.read(config_path)

        # Load the tours details to determine each flag to which camera belongs
        with open(config['general']['tours_details_path'], 'r', encoding='utf-8') as config_file:
            tours_config = json.load(config_file)

        self.cam181_flags = self._create_flags_in_tour_set(tours_config, '181')
        self.cam191_flags = self._create_flags_in_tour_set(tours_config, '191')

        self.ptz_modi_dir = config['general']['ptz_modi_file']
        # Load both cameras pre-calculated PTZ modification files
        self.ptz_modifications_files = {
            '181': self._read_ptz_modi_file('181'),
            '191': self._read_ptz_modi_file('191')
        }
        # Conversion from cm to pixel in the drone image
        self.s = float(config['general']['s'])
        self.s_cm = 1 / self.s

        # Size of all the flag images
        self.image_width = int(config['general']['image_width'])
        self.image_height = int(config['general']['image_height'])

        # Center of all the flag images
        self.center = [self.image_width / 2, self.image_height / 2]

        # Pixel location of the north camera on the drone image
        self.north_cam_x = int(config['general']['north_cam_x'])
        self.north_cam_y = int(config['general']['north_cam_y'])

        # Pixel location of the south camera on the drone image
        self.south_cam_x = int(config['general']['south_cam_x'])
        self.south_cam_y = int(config['general']['south_cam_y'])

        self.north_cam_loc = np.array([self.north_cam_x, self.north_cam_y, 0]).reshape(-1, 1)
        self.south_cam_loc = np.array([self.south_cam_x, self.south_cam_y, 0]).reshape(-1, 1)

        self.cam_loc_in_cm = np.array([0,0,266]).reshape(-1,1)


    # This function take a list of flags that belongs to camera and insert them into a set
    def _create_flags_in_tour_set(self, tours_config, cam_name):
        tours_details = tours_config['tours_details']
        return set(tours_details[cam_name]['flags_ids'])


    # This function read the PTZ modification CSV file
    def _read_ptz_modi_file(self, cam_number):
        rel_column = ['ptz_num', 'pitch', 'yaw', 'f']
        ptz_modi_file_path = f'{self.ptz_modi_dir}/PTZCamValues{cam_number}_mod.txt'
        print(f'Loading file {ptz_modi_file_path}...')
        try:
            # Read PTZ modification file    
            ptz_modi_file = pd.read_csv(ptz_modi_file_path, sep='\t', usecols=rel_column)
        except FileNotFoundError:
            print(f"Error: The PTZ modification {ptz_modi_file_path} file does not exist in the dir.")
            exit()

        return ptz_modi_file


    # This function creates the calibration matrix K
    def _make_k(self, f):
        K = np.zeros((3, 3))
        K[0, 0] = f
        K[1, 1] = f
        K[2, 2] = 1
        K[0, 2] = self.center[0]
        K[1, 2] = self.center[1]
        return K

    # This function calculates the p for the location of the terns
    def _calc_p(self, tern_loc_df, r, k):
        u = tern_loc_df['tern_x'].values
        v = tern_loc_df['tern_y'].values
        one = np.ones (len(u))
        u_v = np.column_stack((u,v,one)).T

        p_o = (np.linalg.inv(r))@ np.linalg.inv(k) @u_v

        #cam_n is the location in cm of the north camera (both in the case of the south and the north cameras)
        # normalize the p-o by dividing the third component (z) to be az the minus z value (height) of the camera
        p_o = p_o/p_o[2]*-self.cam_loc_in_cm[2]

        # p = p_o + cam (the z value qill be 0)
        p = p_o + self.cam_loc_in_cm

        return (p)


    # Calculate the p for of the box (x1,x2,y1,y2)
    def _calc_p_x1_x2(self, tern_loc_df, r, k):
        u = tern_loc_df['x1'].values
        v = tern_loc_df['y1'].values
        one = np.ones (len(u))
        u_v_1 = np.column_stack((u,v,one)).T

        u2 = tern_loc_df['x2'].values
        v2 = tern_loc_df['y2'].values
        one = np.ones (len(u))
        u_v_2 = np.column_stack((u2,v2,one)).T

        ## (u,v,1) = r*k*(p-o)
        ## p-o = r-1 * k-1 * (u,v,1)

        p_o_1 = (np.linalg.inv(r))@ np.linalg.inv(k) @u_v_1
        p_o_2 = (np.linalg.inv(r))@ np.linalg.inv(k) @u_v_2

        ## cam_loc_in_cm is the location in cm of the north camera (both in the case of the south and the north cameras)
        ## normalize the p-o by dividing the third component (z) to be az the minus z value (height) of the camera
        p_o_1 = p_o_1/p_o_1[2]*-self.cam_loc_in_cm[2]
        p_o_2 = p_o_2/p_o_2[2]*-self.cam_loc_in_cm[2]

        # p = p_o + cam (the z value qill be 0)
        p_1 = p_o_1 + self.cam_loc_in_cm
        p_2 = p_o_2 + self.cam_loc_in_cm

        return (p_1, p_2)


    def _tern_loc_pix(self, s, cam_loc_pix, tern_real_loc):
        tern_pix_drone = (tern_real_loc*s) + cam_loc_pix.reshape(-1,1)

        tern_pix_drone = tern_pix_drone[0:2,:].T
        tern_pix_drone = tern_pix_drone.astype(np.int32)

        return (tern_pix_drone)


    def calc_box_location(self, boxes_info, ptz_num):
        # Calculate the tern coordinates
        boxes_info['tern_x'] = (boxes_info['x1'] + boxes_info['x2']) / 2
        boxes_info['tern_y'] = boxes_info['y2']

        ## adding dy/dx ratio
        boxes_info['dy/dx_uv'] = abs(( boxes_info['y2'] - boxes_info['y1']) / (boxes_info['x2'] - boxes_info['x1'] ))

        # Calculate pitch and yaw based on the provided flag number and camera number
        df_cam = self.df_ptz_modi[self.df_ptz_modi['ptz_num'] == ptz_num]

        if df_cam.empty:
            raise ValueError(f"No data found for ptz_num {ptz_num}.")

        pitch, yaw, focal_length = df_cam['pitch'], df_cam['yaw'], df_cam['f']

        r = R.from_euler('zyx', [yaw, 0, pitch],degrees=True).as_matrix()

        k = self._make_k(focal_length)

        # the location in cm in the north camera coordinate
        p = self._calc_p(boxes_info, r, k)

        # calculate the terns locations in pixel of the drone
        # when calculate in pixels, in the south camera we need to use te south camera location (south_cam_loc)
        tern_loc_drone = self._tern_loc_pix(self.s, self.north_cam_loc, p)

        return pd.DataFrame(tern_loc_drone, columns=['box_x_pix_drone', 'box_y_pix_drone'])


    def calc_box_size(self, boxes_info):
        # Create an empty DataFrame
        boxes_size_df = pd.DataFrame()

        ptz_num = int(boxes_info.iloc[0]['flag'])
        # print(ptz_num)

        if ptz_num in self.cam181_flags:
            df_ptz_modi = self.ptz_modifications_files['181']
            cam_drone_loc = self.south_cam_loc
        elif ptz_num in self.cam191_flags:
            df_ptz_modi = self.ptz_modifications_files['191']
            cam_drone_loc = self.north_cam_loc
        else:
            raise Exception(f'The flag {ptz_num} does not found to belong to any camera.')

        # Calculate the tern coordinates
        boxes_size_df['tern_x'] = (boxes_info['x1'] + boxes_info['x2']) / 2
        boxes_size_df['tern_y'] = boxes_info['y2']
        ## adding dy/dx ratio
        boxes_size_df['dy/dx_uv'] = abs(( boxes_info['y2'] - boxes_info['y1']) / (boxes_info['x2'] - boxes_info['x1'] ))
        # Calculate pitch and yaw based on the provided flag number and camera number

        df_cam = df_ptz_modi[df_ptz_modi['ptz_num'] == ptz_num].iloc[0]

        if df_cam.empty:
            raise ValueError(f"No data found for ptz_num {ptz_num}.")

        pitch, yaw, f = df_cam['pitch'], df_cam['yaw'], df_cam['f']

        r = R.from_euler('zyx', [yaw, 0, pitch], degrees=True).as_matrix()

        k = self._make_k(f)

        # Calculate the location in cm
        p_1, p_2 = self._calc_p_x1_x2(boxes_info, r, k)

        box_loc_drone_1, box_loc_drone_2 = self.box_loc_pix(self.s, cam_drone_loc, p_1, p_2)

        boxes_size_df['pix_x1'] = box_loc_drone_1[:,0]
        boxes_size_df['pix_y1'] = box_loc_drone_1[:,1]
        boxes_size_df['pix_x2'] = box_loc_drone_2[:,0]
        boxes_size_df['pix_y2'] = box_loc_drone_2[:,1]

        DX_cm = abs(p_2[0] - p_1[0])
        dx_pix_drone = abs(box_loc_drone_1[:,0] - box_loc_drone_2[:,0])
        dy_pix_drone = abs(box_loc_drone_1[:,1] - box_loc_drone_2[:,1])
        DY_cm = boxes_size_df['dy/dx_uv'] * DX_cm
        area = DX_cm * DY_cm

        boxes_size_df['DX_cm'] =  DX_cm
        boxes_size_df['DY_cm'] =  DY_cm
        boxes_size_df['dx_pix_drone'] = dx_pix_drone
        boxes_size_df['dy_pix_drone'] = dy_pix_drone
        boxes_size_df['Area'] =  area

        return boxes_size_df


    ## the location of the box in pixel on the drone image
    def box_loc_pix(self, s,cam_loc_pix, p1, p2):
        box_pix_drone_1 = (p1*s) + cam_loc_pix.reshape (-1,1)
        box_pix_drone_2 = (p2*s) + cam_loc_pix.reshape (-1,1)

        box_pix_drone_1 = box_pix_drone_1[0:2,:].T
        box_pix_drone_1 = box_pix_drone_1.astype (np.int32)

        box_pix_drone_2 = box_pix_drone_2[0:2,:].T
        box_pix_drone_2 = box_pix_drone_2.astype (np.int32)


        return (box_pix_drone_1, box_pix_drone_2)
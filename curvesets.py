__author__ = 'lucas'

import glob
import os.path
import FATS
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neighbors import KDTree
import json
import random
import cPickle as pickle

class MachoCurvesSet:
    def __init__(self,root_path, regression_resolution,sample_size=None):
        self.root_path = root_path
        self.files_list = []
        self.__explore_folder(root_path)
        if sample_size is not None:
            self.files_list = random.sample(self.files_list, sample_size)
        self.sample_size = len(self.files_list)
        self.resolution = regression_resolution
        self.previous_indexes = []

    def __explore_folder(self,path):
        subdirectories = glob.glob(os.path.join(path, "*"))
        subfolders = [folder for folder in subdirectories if os.path.splitext(folder)[1] == '']
        lc_files = [direct for direct in subdirectories if os.path.splitext(direct)[1] == '.mjd']
        self.files_list += lc_files
        for folder in subfolders:
            self.__explore_folder(folder)

    def __load_curves(self):
        self.original_curves = []
        self.regressed_curves = None
        for path in self.files_list:
            lc = MachoCurvesSet.fold(MachoCurvesSet.get_data_from_file(path))
            rc = MachoCurvesSet.KNNregression(lc, self.resolution)[:,1]
            self.original_curves += [lc]
            if self.regressed_curves is None:
                self.regressed_curves = rc
            else:
                self.regressed_curves = np.vstack((self.regressed_curves,rc))
        self.X = self.regressed_curves


    def __build_kd_tree(self):
        self.kd_tree = KDTree(self.X)

    def __get_new_index(self, current_index):
        dist, ind = self.kd_tree.query(self.X[current_index], k=self.sample_size)
        indexes = ind.tolist()[0][1:]
        for i in indexes:
            if i not in self.previous_indexes:
                return i
        return None

    def get_first(self, index):
        self.previous_indexes = []
        return self.get_next(index)

    def get_next(self,new_index=None):
        if new_index is None:
            new_index = self.__get_new_index(self.current_index)
        self.previous_indexes.append(new_index)
        self.current_index = new_index
        return (self.files_list[new_index], self.original_curves[new_index], self.regressed_curves[new_index])


    def plot_sorted_sequence(self,first_index):
        self.previous_indexes = []
        self.__plot_next(first_index)


    def __plot_next(self,first_index):
        linspace = np.linspace(0,1,self.resolution)
        lc = self.original_curves[first_index]
        MachoCurvesSet.plot_light_curve(lc,self.files_list[first_index])
        new_index = self.__get_new_index(first_index)
        self.previous_indexes.append(new_index)
        if new_index is not None:
            self.__plot_next(new_index)

    def load_and_index_curves(self):
        self.__load_curves()
        self.__build_kd_tree()

    @staticmethod
    def KNNregression(lc, resolution):
        linspace = np.matrix(np.linspace(0,1,num=resolution)).T
        knn = KNeighborsRegressor(n_neighbors=3)
        X =  np.matrix(lc[:,0]).T
        y = lc[:,1]
        y_ = knn.fit(X, y).predict(linspace)
        rlc = np.column_stack((np.array(linspace),y_))
        return rlc

    @staticmethod
    def fold(light_curve):
        [mag, time, error] = [light_curve[:,1], light_curve[:,0], light_curve[:,2]]
        preproccesed_data = FATS.Preprocess_LC(mag, time, error)
        [mag, time, error] = preproccesed_data.Preprocess()
        c = np.array([mag, time, error])
        a = FATS.FeatureSpace(Data=['magnitude','time','error'], featureList=['PeriodLS'])
        a = a.calculateFeature([mag,time,error])
        d = a.result(method='dict')
        T = d['PeriodLS']
        phase = (time %  T)/T
        return np.column_stack((phase,mag,error))


    @staticmethod
    def get_data_from_file(path):
        return pd.DataFrame.from_csv(path,sep=' ',header=2, index_col=None).values


    @staticmethod
    def plot_light_curve(folded_light_curve, file_name=None):
        phase = folded_light_curve[:,0]
        mag = folded_light_curve[:,1]
        plt.plot(phase, mag, '*')
        plt.xlabel("Phase")
        plt.ylabel("Magnitude")
        plt.gca().invert_yaxis()
        if(file_name is not None):
            plt.title(file_name)
        plt.show()

    @staticmethod
    def curve_tuple_to_json(curve_tuple):
        original_length = curve_tuple[1].shape[0]
        regressed_length = len(curve_tuple[2])
        original_curve = curve_tuple[1][:,[0,1]]
        linspace = np.linspace(0,1,regressed_length)
        regressed_curve = np.column_stack((linspace,curve_tuple[2]))
        original_curve_values = []
        regressed_curve_values = []
        for i in range(original_length):
            original_curve_values.append({'x':original_curve[i,0], 'y':original_curve[i,1]})
        for i in range(regressed_length):
            regressed_curve_values.append({'x':linspace[i], 'y':regressed_curve[i]})
        original_curve_data = {'key':'original', 'values':original_curve_values}
        regressed_curve_data = {'key':'regressed', 'values':regressed_curve_values}
        data = [original_curve_data, regressed_curve_data]
        return json.dumps({'name':curve_tuple[0],'data':data})

#Author: Laura Dal Toso 
#Date: 31 May 2022
#Based on work by: Anna Mira, Richard Burns
#------------------------------------------------------------
#Use this script to post process GPFiles and SliceInfo files, and 
#check that all required labels are present
#Before running: 
#- check relative paths
#- check that variables 'contour_file' and 'metadata_file' match your files
#- comment functions that are not needed. 
#    (i.e. if septum points are present, comment 'find_timeframe_septum')

#------------------------------------------------------------


import Contours as cont
from CVI42XML import *
from pathlib import Path
import time

def CleanGPFile(folder, **kwargs):

    '''
    This function perfoms post- processing operations on GPFiles and SliceInfoFiles
    Input: path to folder containing the SliceInfoFile and GPFile
    Otput: new GPFiles and SLiceInfoFiles that can be used as input for the BiVFitting module

    '''

    if 'iter_num' in kwargs:
        # if many processes are run in parallel, assign each one to a different CPU
        iter_num = kwargs.get('iter_num', None)
        pid = os.getpid()
        # assign a new process ID and a new CPU to the child process 
        os.system("taskset -cp %d %d" %(iter_num, pid))
    
    #extract patient name
    case =  os.path.basename(os.path.normpath(folder))
    print('case: ', case )

    # define path to input GPfile and SliceInfoFile
    contour_file = os.path.join(folder, 'GP_ED.txt') 
    metadata_file = os.path.join(folder,'SliceInfo.txt')

    #total_stack = ImageStack(input_dir, dicom_extension='dcm')

    contours  = cont.Contours()

    contours.read_gp_files(contour_file,metadata_file)
    contours.clean_LAX_contour()

    try:
        contours.find_timeframe_septum()
    except:
        err = 'Computing septum'
        print(case, 'Fail',err)
        #print('\033[1;33;41m  {0}\t{1}\t\t\t{2}'.format(case, 'Fail', err))


    try:
        contours.find_timeframe_septum_inserts(time_frame=time_frames)
    except:
        err = 'Computing inserts'
        print(case, 'Fail',err)
        #print('\033[1;33;41m  {0}\t{1}\t\t\t{2}'.format(case, 'Fail',err))

    try:
        contours.find_apex_landmark(time_frame=time_frames)
    except:
        err = 'Computing apex'
        print('\033[1;33;41m  {0}\t{1}\t\t\t{2}'.format(case, 'Fail',err))

    try:
        #contours.find_timeframe_valve_landmarks()
        phases = time_frames
        if 'LAX_LV_EXTENT' in contours.points.keys():
            for index,point in enumerate(contours.get_timeframe_points(
                                'LAX_LV_EXTENT', phases)[1]):
                # the extents has 3 points, for each extent we need to
                # select the first 2 corresponding to the valve
                # the output from get_timeframe_points is already sorted by timeframe
                # therefor we pick the firs to points by timeframe

                # In this dataset the LAX_EXTENT in 3CH is not corresponding to
                # the mitral valve so we need to exclude them
                # if there are aorta points on the same timeframe
                # then is a 3ch and we need to exclude them
                aorta_points,_ = contours.get_frame_points('AORTA_VALVE',
                                                        point.sop_instance_uid)
                atrial_extend,_ = contours.get_frame_points('LAX_LA_EXTENT',
                                                            point.sop_instance_uid)
                if len(aorta_points)>0:
                    continue
                if len(atrial_extend)>0:
                    continue
                if (index+1) % 3 !=0:
                    contours.add_point('MITRAL_VALVE',point)
            del contours.points['LAX_LV_EXTENT']

        if 'LAX_LA_EXTENT' in contours.points.keys():
            for index, point in enumerate(contours.get_timeframe_points(
                'LAX_LA_EXTENT', phases)[1]):
                if(index +1)%3 !=0:
                    contours.add_point('MITRAL_VALVE', point)
            del contours.points['LAX_LA_EXTENT']

        if 'LAX_RV_EXTENT' in contours.points.keys():
            for index,point in enumerate(contours.get_timeframe_points(
                    'LAX_RV_EXTENT',phases)[1]):
                if (index + 1) % 3 != 0:
                    contours.add_point('TRICUSPID_VALVE', point)
            del contours.points['LAX_RV_EXTENT']
    except:
            err = 'Computing valve landmarks'
            print(case, 'Fail',err)
            #print( '\033[1;33;41m  {0}\t{1}\t\t\t{2}'.format(case, 'Fail',err))


    cvi_cont = CVI42XML()
    cvi_cont.contour = contours

    output_gpfile = os.path.join(folder,'GP_ED_proc.txt')
    output_metafile = os.path.join(folder,'SliceInfo_proc.txt')

    cvi_cont.export_contour_points(output_gpfile)
    cvi_cont.export_dicom_metadata(output_metafile)



def split_in_chunks(a, n):
    '''
    This function splits the list a in n chunks.
    Otput: list made of n lists

    '''
    k, m = divmod(len(a), n)
    return list(a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))
  

def split_and_run(cases_list, workers):
    '''
    This function splits the total workload in chunks of equal size and runs the code in parallel.
    Input:
    cases_folder = list of paths to GPFiles
    workers = number of CPUs to be used
    '''

    # split the total workload in chunks of equal size
    n_chunks = int(np.ceil(len(cases_list)/workers))

    print('TOT CASES:', len(cases_list))
    print('TOT CPUs selected: ', workers )
    print('-----> DATA WILL BE SPLIT INTO ', n_chunks, ' chunks')
    
    # create a Log file where to store failed cases
    #FailedCases = Path(os.path.join('./results/' ,'FailedCases.txt'))
    #FailedCases.touch(exist_ok=True)

    if workers == 1: 
        results = [CleanGPFile(case) for case in cases_list]

    if n_chunks <=1:
        # spawn a number of child processes equal to the number of patients in each chunk
        with concurrent.futures.ProcessPoolExecutor(max_workers= workers) as executor:
            #the CPU affinity is changed by perform_fitting, so that each child process is assigned to one CPU 
            for i,folder in enumerate(cases_list):   
                results = executor.submit(CleanGPFile, folder, iter_num = i) 

    if n_chunks >1:
        # split data in n chunks:
        split_folders = split_in_chunks(cases_list, n_chunks)
        
        # create a Log file where to store failed cases
        FailedCases = Path(os.path.join('../results/' ,'FailedCases.txt'))
        FailedCases.touch(exist_ok=True)   

        for subfolders in split_folders:
            with open(FailedCases, 'a') as f:
                f.write('In this chunk, cases: '+ str(subfolders) +'\n') 
            
            futures = []
            # spawn a number of child processes equal to the number of patients in each chunk
            with concurrent.futures.ProcessPoolExecutor(max_workers= workers) as executor:
 
                for i,folder in enumerate(subfolders):
                    results = executor.submit(CleanGPFile, folder, iter_num = i)
                    #print( results.result()) #do this is you want to interrupt program when case fails
                    #futures.append( (results, os.path.basename(os.path.normpath(folder))))



if __name__ == '__main__':

    
    startLDT = time.time()
    workers = 6 # number of CPUs to be used in parallel to process the data

    # Create some data
    working_dir = '../Fitting_Framework'   #edit to your relative path to this data

    cases_folder = os.path.join(working_dir, 'test_data')
    cases_list = [os.path.join(cases_folder, batch) for batch in os.listdir(cases_folder)]

    # this lists all the subfolders in the test_data folder
    results = split_and_run(cases_list, workers)
    print('TOTAL TIME: ', time.time()-startLDT)


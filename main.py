"""
date: 2017/11/10
author: lslcode [jasonli8848@qq.com]
"""

import os
import gc
import xml.etree.ElementTree as etxml
import random
import skimage.io
import skimage.transform
import numpy as np
import tensorflow as tf
import ssd300
import time

'''
SSD检测
'''
def testing():
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9)
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        ssd_model = ssd300.SSD300(sess,False)
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver(var_list=tf.trainable_variables())
        if os.path.exists('./session_params/session.ckpt.index') :
            saver.restore(sess, './session_params/session.ckpt')
            image, actual,file_list = get_traindata_voc2012(1)
            print('file_list:' + str(file_list))
            for img, act in zip(image, actual):
                pred_class,pred_location = ssd_model.run([img],None)
                
                #print('end time : ' + time.asctime(time.localtime(time.time())))
                print('pred_class:' + str(pred_class))
                print('pred_location:' + str(pred_location))
                '''
                for a in act :
                    print('actual:' + str(a))
                    for c,l in zip(pred_class,pred_location):
                        if(np.argmax(c) == a[4]):
                            print('f_class:' + str(a[4])+' - '+str(np.amax(c)))
                            print('f_location:' + str(l))
                            print('----------------------')
                '''           
        else:
            print('No Data Exists!')
            
        sess.close()
    
'''
SSD训练
'''
def training():
    batch_size = 11
    running_count = 0
    
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9)
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        ssd_model = ssd300.SSD300(sess,True)
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver(var_list=tf.trainable_variables())
        if os.path.exists('./session_params/session.ckpt.index') :
            print('\nStart Restore')
            saver.restore(sess, './session_params/session.ckpt')
            print('\nEnd Restore')
         
        print('\nStart Training')
        min_loss_location = 100000.
        min_loss_class = 100000.
        while((min_loss_location + min_loss_class) > 0.001 and running_count < 20050):
            running_count += 1
            
            train_data, actual_data,_ = get_traindata_voc2012(batch_size)
            
            if len(train_data) > 0:
                loss_all,loss_class,loss_location,pred_class,pred_location = ssd_model.run(train_data, actual_data)
                l = np.sum(loss_location)
                c = np.sum(loss_class)
                if min_loss_location > l:
                    min_loss_location = l
                if min_loss_class > c:
                    min_loss_class = c
               
                print('Running:【' + str(running_count) + '】|Loss All:【'+ str(loss_all) + '】|Location:【'+ str(np.sum(loss_location)) + '】|Class:【'+ str(np.sum(loss_class)) + '】|pred_class:【'+ str(np.sum(pred_class))+'|'+str(np.amax(pred_class))+'|'+ str(np.amin(pred_class)) + '】|pred_location:【'+ str(np.sum(pred_location))+'|'+str(np.amax(pred_location))+'|'+ str(np.amin(pred_location)) + '】')
                #print('Running:【' + str(running_count) + '】|Loss All:【' + str(min_loss_location + min_loss_class) + '/' + str(loss_all) + '】|Location:【' + str(min_loss_location) + '/' + str(np.sum(loss_location)) + '】|Class:【' + str(min_loss_class) + '/' + str(np.sum(loss_class)) + '】')
                #print('loss_location:'+str(loss_location))
                #print('loss_class:'+str(loss_location))
                
                # 定期保存ckpt
                if running_count % 50 == 0:
                    saver.save(sess, './session_params/session.ckpt')
                    gc.collect()
            else:
                print('No Data Exists!')
                break
            
        saver.save(sess, './session_params/session.ckpt')
        sess.close()
        gc.collect()
            
    print('End Training')
    
'''
获取voc2012训练图片数据
train_data：训练批次图像，格式[None,width,height,3]
actual_data：图像标注数据，格式[None,[None,top_x,top_y,width,height,lable]]
'''
file_name_list = os.listdir('./train_datasets/voc2012/JPEGImages/')
def get_traindata_voc2012(batch_size):
    def get_actual_data_from_xml(xml_path):
        lable_arr = ['aeroplane','bicycle','bird','boat','bottle','bus','car','cat','chair','cow','diningtable','dog','horse','motorbike','person','pottedplant','sheep','sofa','train','tvmonitor']
        actual_item = []
        try:
            annotation_node = etxml.parse(xml_path).getroot()
            img_width =  float(annotation_node.find('size').find('width').text.strip())
            img_height = float(annotation_node.find('size').find('height').text.strip())
            object_node_list = annotation_node.findall('object')       
            for obj_node in object_node_list:                       
                lable = lable_arr.index(obj_node.find('name').text.strip())
                bndbox = obj_node.find('bndbox')
                x_min = float(bndbox.find('xmin').text.strip())
                y_min = float(bndbox.find('ymin').text.strip())
                x_max = float(bndbox.find('xmax').text.strip())
                y_max = float(bndbox.find('ymax').text.strip())
                # 位置数据用比例来表示，格式[top_x,top_y,width,height,lable]
                actual_item.append([(x_min / img_width), (y_min / img_height), ((x_max - x_min) / img_width), ((y_max - y_min) / img_height), lable])
            return actual_item  
        except:
            return None
        
    train_data = []
    actual_data = []
    
    file_list = random.sample(file_name_list, batch_size)
    
    for f_name in file_list :
        img_path = './train_datasets/voc2012/JPEGImages/' + f_name
        xml_path = './train_datasets/voc2012/Annotations/' + f_name.replace('.jpg','.xml')
        if os.path.splitext(img_path)[1].lower() == '.jpg' :
            actual_item = get_actual_data_from_xml(xml_path)
            if actual_item != None :
                actual_data.append(actual_item)
            else :
                print('Error : '+xml_path)
                continue
            img = skimage.io.imread(img_path)
            img = skimage.transform.resize(img, (300, 300))
	         # 由于检测出来的结果loc与class的值范围[0,1]，为了预防梯度弥散，输入数值需要转换为范围一致的数值，包括后续初始化的卷积核
            img = img / 255
            img = np.array(img, dtype=np.float32)
            img = img.reshape((300, 300, 3))
            train_data.append(img)
            
    return train_data, actual_data,file_list

 
'''
主程序入口
'''
if __name__ == '__main__':
    print('\nStart Running')
    # 检测
    #testing()
    # 训练
    training()
    print('\nEnd Running')
   
        

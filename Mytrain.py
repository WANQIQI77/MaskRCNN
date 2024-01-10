# -*- coding: utf-8 -*-

import os
import sys
import random
import math
import re
import time
import numpy as np
import cv2
# import matplotlib
# import matplotlib.pyplot as plt
import tensorflow as tf
from mrcnn.config import Config
# import utils
from mrcnn import model as modellib, utils
from mrcnn import visualize
import yaml
from mrcnn.model import log
from PIL import Image
# from sklearn.model_selection import train_test_split

# os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# Root directory of the project
ROOT_DIR = os.getcwd()  # 获取当前工作目录

# ROOT_DIR = os.path.abspath("../")
# Directory to save logs and trained model
MODEL_DIR = os.path.join(ROOT_DIR, "logs")

iter_num = 0

# Local path to trained weights file
MODEL_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")


# Download COCO trained weights from Releases if needed
# if not os.path.exists(MODEL_PATH):
#     utils.download_trained_weights(MODEL_PATH)


class ShapesConfig(Config):
    """Configuration for training on the toy shapes' dataset.
    Derives from the base Config class and overrides values specific
    to the toy shapes' dataset.
    """
    # Give the configuration a recognizable name
    NAME = "shapes"

    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1

    # Number of classes (including background)
    NUM_CLASSES = 8 + 1  # background + 1 shapes  注意这里我是2类，所以是2+1

    # Use small images for faster training. Set the limits of the small side
    # the large side, and that determines the image shape.
    IMAGE_MIN_DIM = 256
    IMAGE_MAX_DIM = 1024

    # Use smaller anchors because our image and objects are small
    # RPN_ANCHOR_SCALES = (8 * 6, 16 * 6, 32 * 6, 64 * 6, 128 * 6)  # anchor side in pixels
    RPN_ANCHOR_SCALES = (16 * 6, 32 * 6, 64 * 6, 128 * 6, 256 * 6)  # 我的图片中目标比较大，所以我把anchor的尺寸也设置的大了一点

    # Reduce training ROIs per image because the images are small and have
    # few objects. Aim to allow ROI sampling to pick 33% positive ROIs.
    TRAIN_ROIS_PER_IMAGE = 100

    # Use a small epoch since the data is simple
    STEPS_PER_EPOCH = 50  # 每个epoch中迭代的step，最好不要改动

    # use small validation steps since the epoch is small
    VALIDATION_STEPS = 50


config = ShapesConfig()
config.display()


class DrugDataset(utils.Dataset):
    # 得到该图中有多少个实例（物体）
    def get_obj_index(self, image):
        n = np.max(image)
        return n

    # 解析labelme中得到的yaml文件，从而得到mask每一层对应的实例标签
    def from_yaml_get_class(self, image_id):
        info = self.image_info[image_id]
        with open(info['yaml_path']) as f:
            # temp = yaml.load(f.read())
            temp = yaml.load(f.read(), Loader=yaml.FullLoader)
            labels = temp['label_names']
            del labels[0]
        return labels

    # 重新写draw_mask
    def draw_mask(self, num_obj, mask, image, image_id):
        # print("draw_mask-->",image_id)
        # print("self.image_info",self.image_info)
        info = self.image_info[image_id]
        # print("info-->",info)
        # print("info[width]----->",info['width'],"-info[height]--->",info['height'])
        for index in range(num_obj):
            for i in range(info['width']):
                for j in range(info['height']):
                    # print("image_id-->",image_id,"-i--->",i,"-j--->",j)
                    # print("info[width]----->",info['width'],"-info[height]--->",info['height'])
                    at_pixel = image.getpixel((i, j))
                    if at_pixel == index + 1:
                        mask[j, i, index] = 1
        return mask

    # 重新写load_shapes，里面包含自己的自己的类别
    # 并在self.image_info信息中添加了path、mask_path 、yaml_path
    # yaml_pathdataset_root_path = "/dateset/"
    # img_floder = dataset_root_path + "rgb"
    # mask_floder = dataset_root_path + "mask"
    # dataset_root_path = "/tongue_dateset/"
    def load_shapes(self, count, img_floder, mask_floder, imglist, dataset_root_path):
        """Generate the requested number of synthetic images.
        count: number of images to generate.
        height, width: the size of the generated images.
        """
        # Add classes
        self.add_class("shapes", 1, "weizhi")
        self.add_class("shapes", 2, "houdu")
        self.add_class("shapes", 3, "huishengdai")
        self.add_class("shapes", 4, "pangguangxian")
        self.add_class("shapes", 5, "xianwo")
        self.add_class("shapes", 6, "xueliu")
        self.add_class("shapes", 7, "gongjing")
        self.add_class("shapes", 8, "shanxing")
        # self.add_class("shapes", 3, "leibie3")
        # self.add_class("shapes", 4, "leibie4")

        for i in range(count):
            # 获取图片宽和高
            print(i)
            filestr = imglist[i].split(".")[0]
            print(filestr)
            # print(imglist[i],"-->",cv_img.shape[1],"--->",cv_img.shape[0])
            # print("id-->", i, " imglist[", i, "]-->", imglist[i],"filestr-->",filestr)
            # filestr = filestr.split("_")[1]
            mask_path = mask_floder + "/" + filestr + ".png"
            img_path = img_floder + "/" + filestr + ".jpg"
            yaml_path = dataset_root_path + "yaml/" + filestr + ".yaml"
            # print(mask_path)
            # print(img_path)
            # print(dataset_root_path + "labelme_json/" + filestr + "/img.png")

            cv_img = cv2.imread(img_path)
            print(type(cv_img))
            self.add_image("shapes", image_id=i, path=img_floder + "/" + imglist[i],
                           width=cv_img.shape[1], height=cv_img.shape[0], mask_path=mask_path, yaml_path=yaml_path)
            # self.add_image("shapes", image_id=i, path=img_floder + "/" + imglist[i],
            #                width=cv_img.shape[1], height=cv_img.shape[0], mask_path=mask_path)

    # 重写load_mask
    def load_mask(self, image_id):
        """Generate instance masks for shapes of the given image ID.
        """
        global iter_num
        print("image_id", image_id)
        info = self.image_info[image_id]
        count = 1  # number of object
        img = Image.open(info['mask_path'])
        num_obj = self.get_obj_index(img)
        mask = np.zeros([info['height'], info['width'], num_obj], dtype=np.uint8)
        mask = self.draw_mask(num_obj, mask, img, image_id)
        occlusion = np.logical_not(mask[:, :, -1]).astype(np.uint8)
        for i in range(count - 2, -1, -1):
            mask[:, :, i] = mask[:, :, i] * occlusion

            occlusion = np.logical_and(occlusion, np.logical_not(mask[:, :, i]))
        labels = []
        labels = self.from_yaml_get_class(image_id)
        labels_form = []
        for i in range(len(labels)):
            if labels[i].find("weizhi") != -1:
                labels_form.append("weizhi")
            elif labels[i].find("houdu") != -1:
                labels_form.append("houdu")
            elif labels[i].find("huishengdai") != -1:
                labels_form.append("huishengdai")
            elif labels[i].find("pangguangxian") != -1:
                labels_form.append("pangguangxian")
            elif labels[i].find("xianwo") != -1:
                labels_form.append("xianwo")
            elif labels[i].find("xueliu") != -1:
                labels_form.append("xueliu")
            elif labels[i].find("gongjing") != -1:
                labels_form.append("gongjing")
            elif labels[i].find("shanxing") != -1:
                labels_form.append("shanxing")

        class_ids = np.array([self.class_names.index(s) for s in labels_form])
        return mask, class_ids.astype(np.int32)


'''
def get_ax(rows=1, cols=1, size=8):
    """Return a Matplotlib Axes array to be used in
    all visualizations in the notebook. Provide a
    central point to control graph sizes.
    Change the default size attribute to control the size
    of rendered images
    """
    _, ax = plt.subplots(rows, cols, figsize=(size * cols, size * rows))
    return ax
'''

if __name__ == '__main__':
    # 基础设置
    dataset_root_path = "D:/project/Placental segmentation/MaskRCNN/train_data/"  # 你的数据的路径
    img_floder = dataset_root_path + "pic"
    mask_floder = dataset_root_path + "cv2_mask"
    # yaml_floder = dataset_root_path
    imglist = os.listdir(img_floder)
    count = len(imglist)

    # 加载数据集
    # train与val数据集相同
    dataset_train = DrugDataset()
    dataset_train.load_shapes(count, img_floder, mask_floder, imglist, dataset_root_path)
    dataset_train.prepare()
    # print("dataset_train-->",dataset_train._image_ids)
    dataset_val = DrugDataset()
    dataset_val.load_shapes(count, img_floder, mask_floder, imglist, dataset_root_path)
    dataset_val.prepare()

    # # 加载数据集
    # dataset = DrugDataset()
    # dataset.load_shapes(count, img_floder, mask_floder, imglist, dataset_root_path)
    # dataset.prepare()
    # train_ids, val_ids = train_test_split(dataset.image_ids, test_size=0.2, random_state=42)
    #
    # print("dataset_val-->",dataset_val._image_ids)

    # Load and display random samples
    # image_ids = np.random.choice(dataset_train.image_ids, 4)
    # for image_id in image_ids:
    #    image = dataset_train.load_image(image_id)
    #    mask, class_ids = dataset_train.load_mask(image_id)
    #    visualize.display_top_masks(image, mask, class_ids, dataset_train.class_names)

    # Create model in training mode
    model = modellib.MaskRCNN(mode="training", config=config,
                              model_dir=MODEL_DIR)

    # Which weights to start with?
    init_with = "imagenet"  # imagenet, coco, or last

    if init_with == "imagenet":
        model.load_weights(model.get_imagenet_weights(), by_name=True)
    elif init_with == "coco":
        # Load weights trained on MS COCO, but skip layers that
        # are different due to the different number of classes
        # See README for instructions to download the COCO weights
        # print(MODEL_PATH)
        model.load_weights(MODEL_PATH, by_name=True,
                           exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",
                                    "mrcnn_bbox", "mrcnn_mask"])
    elif init_with == "last":
        # Load the last model you trained and continue training
        model.load_weights(model.find_last()[1], by_name=True)

    # Train the head branches
    # Passing layers="heads" freezes all layers except the head
    # layers. You can also pass a regular expression to select
    # which layers to train by name pattern.
    model.train(dataset_train, dataset_val,
                learning_rate=config.LEARNING_RATE,
                epochs=10,
                layers='heads')  # 固定其他层，只训练head，epoch为10

    # Fine tune all layers
    # Passing layers="all" trains all layers. You can also
    # pass a regular expression to select which layers to
    # train by name pattern.
    model.train(dataset_train, dataset_val,
                learning_rate=config.LEARNING_RATE / 10,
                epochs=10,
                layers="all")  # 微调所有层的参数，epoch为10

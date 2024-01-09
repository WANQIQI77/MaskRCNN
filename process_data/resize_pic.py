import os
from  PIL import Image
import cv2


def resize_pic(folder_path, output_folder, new_size=(512, 512)):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    images_files = [f for f in os.listdir(folder_path) if f.endswith(('.jpg','.png'))]

    for image_file in images_files:
        input_path = os.path.join(folder_path, image_file)
        output_path = os.path.join(output_folder, image_file)

        # 打开图片
        with Image.open(input_path) as img:
            # 调整大小
            resized_img = img.resize(new_size)

            # 保存调整大小后的图片
            resized_img.save(output_path)


if __name__=='__main__':
    folder_path = "../train_data/cv2_mask_original"
    output_folder = "../train_data/cv2_mask"
    resize_pic(folder_path, output_folder)
    print("Done")
from PIL import Image
import imagehash
import argparse
import shelve
import glob
import os
import xml.etree.ElementTree as ET
import uuid
import inspect
import sys
from PIL import Image
import imagehash
import shutil
import tqdm
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, os.path.join(parentdir, 'server/flask-faster-rcnn'))
sys.path.insert(0, os.path.join(parentdir, 'data-augmentation'))

import annotation


db = {}


def make_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def generate(args):
    if os.path.exists(args['output']):
        shutil.rmtree(args['output'])
    make_dir(args['output'])

    for imageCrop in tqdm.tqdm(glob.glob(args['catalog'] + "/*/*.jpg"), desc='loading catalog'):    
        catalog_class_name = os.path.basename(os.path.normpath(os.path.dirname(imageCrop)))
        image = Image.open(imageCrop)
        h = str(imagehash.phash(image))
        db[h] = catalog_class_name

    for annotationPath in tqdm.tqdm(glob.glob(os.path.join(args['annotation_input'], "*.xml"))):
        tree = ET.parse(annotationPath)
        root = tree.getroot()
        filename = os.path.basename(annotationPath)
        filename, _ = os.path.splitext(filename)
        if not os.path.exists(os.path.join(args['image_input'], filename + '.jpg')):
            print os.path.join(args['image_input'], filename + '.jpg')
            continue
        image = Image.open(os.path.join(args['image_input'], filename + '.jpg'))
        for item in tree.findall('.//object'):
            
            class_name = item.find('name').text
            bndbox = item.find('bndbox')
            xmin = int(bndbox.find('xmin').text)
            xmax = int(bndbox.find('xmax').text)
            ymin = int(bndbox.find('ymin').text)
            ymax = int(bndbox.find('ymax').text)

            cropname = str(uuid.uuid4()) + '.jpg'
            crop = image.crop((xmin, ymin, xmax, ymax))
            croptempfile = os.path.join("/tmp", cropname)
            crop.save(croptempfile, quality=100, subsampling=0)
            croptemp = Image.open(croptempfile)
            os.remove(croptempfile)
            h = str(imagehash.phash(croptemp))
            if h in db:
                if db[h] == 'neg':
                    item.find('name').text = 'neg'
                    root.remove(item)
                else:
                    item.find('name').text = db[h]
            else:
                if args['remove']:
                    root.remove(item)
                print "not found image with the same hash for one of the crops in : " + filename , " remove: ", args['remove']
        #print os.path.join(args['output'], os.path.basename(annotationPath))
        with open(os.path.join(args['output'], os.path.basename(annotationPath)), "w") as xmlfile:
            xmlfile.write(annotation.prettify(root))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tool to generate the correct XML annotations in the ned of the pipeline')
    parser.add_argument('-i', '--image_input', dest='image_input', help="path to folder including the original images", required=True)
    parser.add_argument('-a', '--annotation_input', dest='annotation_input', help="path to folder including the box annotations", required=True)
    parser.add_argument('-o', '--output', dest='output', help="path to the output folder", required=True)
    parser.add_argument('-c', '--catalog', dest='catalog', help="path to the directory containing subdirectories filled with the crops related to the directory's name", required=True)
    parser.add_argument('--remove_not_exists', help='if True remove the pictures', dest="remove", default=False, action="store_true")
    args = vars(parser.parse_args())

    generate(args)
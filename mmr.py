__author__ = 'jncl'
"""
---------------------------
Name: MyMediaRenamer.py
Author: jncl
Version: 0.1.1

DESCRIPTION:
   A script to consistently rename photo and video files from various sources using EXIF timestamps!

   Files are renamed as:

       YYYY_MMDD_HHMMSS(_####)_$$$(_???).ext

       YYYY: year
       MM:   month
       DD:   day
       HH:   hour
       MM:   minute
       SS:   second
       ####: image number (from original file name if present)
       $$$:  camera tag (from directory name)
       ???:  other tag in original file name if present

USAGE:
   mmr.py --directory '<full path to directory>' [--recursive]

---------------------------
"""



import argparse
import sys
import os
import datetime
import re
import exiftool
import config


class ArgsManager:
    parser = None
    args = None
    directory = ''
    is_recursive = False

    @staticmethod
    def setup_parser():
        parser = argparse.ArgumentParser(__file__,
                                         description='A script to rename video files in the format YYYY_MMDD_HHMMSS_####',
                                         formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--directory', dest='directory', action='store', metavar='<path to video files',
                            help='Full path to directory with video files to rename.', required=True)
        parser.add_argument('--recursive', dest='is_recursive', action='store_true', default=False,
                            help='Process given directory recursively.')
        return parser

    @staticmethod
    def parse_args():
        if ArgsManager.parser is None:
            ArgsManager.parser = ArgsManager.setup_parser()
        if ArgsManager.args is None:
            ArgsManager.args = ArgsManager.parser.parse_args()
        ArgsManager.directory = ArgsManager.args.directory
        print('--directory: ' + ArgsManager.directory)
        print()
        if not os.path.exists(ArgsManager.directory):
            print('Path does not exist: ' + ArgsManager.directory)
            sys.exit()
        ArgsManager.is_recursive = ArgsManager.args.is_recursive


class MyMediaRenamerBase:
    photo_ext_list = ['nef', 'jpg', 'jpeg', 'mpo', 'png']
    video_ext_list = ['mov', 'mp4']
    all_ext_list = photo_ext_list + video_ext_list

    unknown_list = 'UNKNOWN LIST-'
    previous_rename_new_date_not_found_list = 'PREVIOUS RENAME, NEW DATE NOT FOUND LIST'
    previous_rename_new_name_list = 'PREVIOUS RENAME, NEW NAME LIST'
    previous_rename_new_date_list = 'PREVIOUS RENAME, NEW DATE LIST'
    previous_rename_match_list = 'PREVIOUS RENAME MATCH LIST-'
    standard_list = 'STANDARD LIST'
    gopro_sequence_list = 'GOPRO SEQUENCE LIST'
    samsung_list = 'SAMSUNG LIST'

    category_list = []
    category_list.append(unknown_list)
    category_list.append(previous_rename_new_date_not_found_list)
    category_list.append(previous_rename_new_name_list)
    category_list.append(previous_rename_new_date_list)
    category_list.append(previous_rename_match_list)
    category_list.append(standard_list)
    category_list.append(gopro_sequence_list)
    category_list.append(samsung_list)


class ExifToolManager:
    et = None

    @staticmethod
    def get_et():
        if ExifToolManager.et is None:
            ExifToolManager.et = exiftool.ExifTool()
        return ExifToolManager.et


class MediaType:
    def __init__(self):
        self.is_photo = False
        self.is_video = False


class FileObject(MyMediaRenamerBase):
    def __init__(self, root, file_name, camera_tag):
        self.root_path = root
        self.file_path = os.path.join(root, file_name)
        self.file_name = file_name
        self.file_parts = self.get_file_parts()
        self.is_media = False
        self.new_file_name_object = None
        self.media_type = MediaType()
        if self.file_parts is not None:
            self.no_ext = self.file_parts[0]
            self.ext = self.file_parts[1].lower()
            if self.ext in self.all_ext_list:
                self.is_media = True
                if self.ext in self.photo_ext_list:
                    self.media_type.is_photo = True
                elif self.ext in self.video_ext_list:
                    self.media_type.is_video = True
                self.new_file_name_object = FileNameObject()

        self.camera_tag = camera_tag
        self.new_file_name = ''

    def get_file_parts(self):
        match = re.findall('(.+?)\.([^.]*$|$)', self.file_name, re.IGNORECASE)
        if len(match) > 0 and len(match[0]) == 2:
            return match[0]
        else:
            return None

    def rename(self):
        os.rename(self.file_path, os.path.join(self.root_path, self.new_file_name))


class FileNameObject:
    def __init__(self):
        self.date_time = None
        self.image_number = None
        self.camera_tag = None
        self.ext = None

    def get_new_file_name(self):
        if self.image_number is None:
            return '{0}_{1}.{2}'.format(self.date_time, self.camera_tag, self.ext)
        return '{0}_{1}_{2}.{3}'.format(self.date_time, self.image_number, self.camera_tag, self.ext)


class FileManager(MyMediaRenamerBase):
    def __init__(self):
        self.category_list_dict = dict((category, []) for category in self.category_list)

    @staticmethod
    def get_date_time_name(fo: FileObject):
        tag_name = ''
        if fo.media_type.is_photo:
            tag_name = 'EXIF:DateTimeOriginal'
        elif fo.media_type.is_video:
            tag_name = 'QuickTime:TrackCreateDate'
        if tag_name == '':
            print('Could not determine the media type!')
            print('file_path = ' + fo.file_path)
            return None

        exif_date_name = ExifToolManager.et.get_tag(tag_name, fo.file_path).replace('/', ':')

        try:
            dt = datetime.datetime.strptime(str(exif_date_name), '%Y:%m:%d %H:%M:%S')
            # print(dt)
            date_time_name = dt.strftime('%Y_%m%d_%H%M%S')
            if date_time_name is not None:
                return date_time_name
        except ValueError:
            return None

    # USE CASE - ALREADY RENAMED
    def already_renamed(self, fo: FileObject):
        # matches files with 4-digit camera numbers or gopro sequence files
        # group 1: date time name
        # group 2: image number
        match = re.findall('(\d{4}_\d{4}_\d{6})_(\d{4}|G\d{7})?.*', fo.file_name, re.IGNORECASE)
        if len(match) == 0:
            return False

        # check date time tag anyway
        # ...unless we don't have an image number! In this case we use the date time in the file name.
        image_number = match[0][1] if len(match[0]) == 2 and match[0][1] != '' else None
        if image_number is not None:
            new_date_time_name = FileManager.get_date_time_name(fo)
            if new_date_time_name is None:
                self.category_list_dict[self.previous_rename_new_date_not_found_list].append(fo.file_path)
                return True
        else:
            new_date_time_name = match[0][0]

        fno = FileNameObject()
        fno.date_time = new_date_time_name
        fno.image_number = image_number
        fno.camera_tag = fo.camera_tag
        fno.ext = fo.ext
        new_file_name = fo.file_name if fno.image_number is None else fno.get_new_file_name()
        if new_file_name == fo.file_name:
            self.category_list_dict[self.previous_rename_match_list].append(fo)
            return True

        fo.new_file_name = new_file_name

        # check date_time_name tag with existing file name
        old_date_time_name = match[0][0]
        if old_date_time_name != new_date_time_name:
            self.category_list_dict[self.previous_rename_new_date_list].append(fo)
        else:
            self.category_list_dict[self.previous_rename_new_name_list].append(fo)
        return True

    # USE CASE - GOPRO SEQUENCE JPG
    def gopro_sequence_jpg(self, fo: FileObject):
        match = re.findall('G\d{3}(\d{4}).jpg', fo.file_name, re.IGNORECASE)
        if len(match) == 0:
            return False

        fno = FileNameObject()
        fno.date_time = FileManager.get_date_time_name(fo)
        fno.image_number = fo.file_name[0:-4]
        fno.camera_tag = fo.camera_tag
        fno.ext = fo.ext
        fo.new_file_name = fno.get_new_file_name()
        self.category_list_dict[self.gopro_sequence_list].append(fo)
        return True

    # USE CASE - SAMSUNG FILE 1
    def samsung_file1(self, fo: FileObject):
        # example: IMG_20130531_163007_Richtone(HDR).jpg
        # group 0: IMG
        # group 1: 2013
        # group 2: 0531
        # group 3: 163007
        # group 4: HDR
        match = re.findall('([a-zA-Z]+)?(?:_)?(\d{4})(\d{4})_(\d{6})(?:[\w+]+)?(?:\()?(HDR)?(?:\))?(?:.*?)', fo.file_name, re.IGNORECASE)
        if len(match) == 0:
            return False
        file_name_parts = match[0]
        fno = FileNameObject()
        fno.date_time = '{0}_{1}_{2}'.format(file_name_parts[1], file_name_parts[2], file_name_parts[3])
        extra_tag = None
        if file_name_parts[0] == 'PANO':
            extra_tag = 'PANO'
        elif file_name_parts[4] == 'HDR':
            extra_tag = 'HDR'
        if extra_tag is not None:
            fno.camera_tag = '{0}_{1}'.format(fo.camera_tag, extra_tag)
        else:
            fno.camera_tag = fo.camera_tag
        fno.ext = fo.ext
        fo.new_file_name = fno.get_new_file_name()
        self.category_list_dict[self.samsung_list].append(fo)
        return True

    # USE CASE - SAMSUNG FILE 2
    def samsung_file2(self, fo: FileObject):
        # example: IMG_20130531_163007_Richtone(HDR).jpg
        # group 0: IMG
        # group 1: 2013
        # group 2: 0531
        # group 3: 163007
        # group 4: HDR
        match = re.findall('(\d{4})-(\d{2})-(\d{2}) (\d+).(\d+).(\d+).*', fo.file_name, re.IGNORECASE)
        if len(match) == 0:
            return False
        file_name_parts = match[0]
        fno = FileNameObject()
        fno.date_time = '{0}_{1}{2}_{3}{4}{5}'.format(file_name_parts[0],
                                                      file_name_parts[1],
                                                      file_name_parts[2],
                                                      file_name_parts[3].zfill(2),
                                                      file_name_parts[4].zfill(2),
                                                      file_name_parts[5].zfill(2))
        fno.camera_tag = fo.camera_tag
        fno.ext = fo.ext
        fo.new_file_name = fno.get_new_file_name()
        self.category_list_dict[self.samsung_list].append(fo)
        return True

    # USE CASE - STANDARD FILE
    def standard_file(self, fo: FileObject):
        match = re.findall('([a-zA-Z_]{4})(\d{4})\.[\w]+', fo.file_name)
        if len(match) == 0:
            return False
        file_name_parts = match[0]
        fno = FileNameObject()
        fno.date_time = FileManager.get_date_time_name(fo)
        if fno.date_time is None:
            return False
        fno.image_number = file_name_parts[1]
        fno.camera_tag = fo.camera_tag
        fno.ext = fo.ext
        fo.new_file_name = fno.get_new_file_name()
        self.category_list_dict[self.standard_list].append(fo)
        return True

    def process_file(self, fo: FileObject):
        # print('Processing: ' + fo.file_name)

        if fo.file_name.lower() == 'thumbs.db':
            return

        # check if file is a media file
        if not fo.is_media:
            self.category_list_dict[self.unknown_list].append(fo)
            return

        # ----------------
        # --- USE CASES --
        # ----------------

        # ALREADY RENAMED
        if self.already_renamed(fo):
            return

        # GOPRO SEQUENCE JPG
        if self.gopro_sequence_jpg(fo):
            return

        # SAMSUNG FILE - (20130518_091828.mp4)
        if self.samsung_file1(fo):
            return

        # SAMSUNG FILE - (2013-02-19 8.46.18.jpg)
        if self.samsung_file2(fo):
            return

        # STANDARD FILE (DSC_1000.JPG)
        if self.standard_file(fo):
            return

        # WHAT IS THIS FILE??!!
        self.category_list_dict[self.unknown_list].append(fo)

    @staticmethod
    def test_this(x):
        return x + 5


class DirectoryManager:
    # parent_name = None
    # camera_tag = None

    @staticmethod
    def get_camera_tag(directory):
        camera_tag = None
        parent_name = os.path.split(directory)[1]
        for item in config.camera_tag_list:
            if item[0].lower() in parent_name.lower():
                camera_tag = item[1]
                break

        if camera_tag is None:
            print()
            print('WARNING: could not determine type of camera from parent directory name...')
            print('         parent directory name: ' + parent_name)
            print()
            print(
                '         Check that one of the names listed under "camera_list" in config.py is in the directory name.')
            print()
            return None
        return camera_tag

    @staticmethod
    def process_directory(directory, fm: FileManager):
        if ArgsManager.is_recursive:
            for root, dir_names, file_names in os.walk(directory):
                for dir_name in dir_names:
                    dir_path = os.path.join(root, dir_name)
                    camera_tag = DirectoryManager.get_camera_tag(dir_path)
                    if camera_tag is None:
                        continue
                    sub_file_names = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
                    for file_name in sub_file_names:
                        fm.process_file(FileObject(dir_path, file_name, camera_tag))
        else:
            camera_tag = DirectoryManager.get_camera_tag(directory)
            if camera_tag is None:
                return
            for root, dirs, file_names in os.walk(directory):
                for file_name in file_names:
                    fm.process_file(FileObject(root, file_name, camera_tag))


class ResultsManager():
    def __init__(self, fm: FileManager):
        self.fm = fm
        self.prompt_for_rename = False

    def print_results(self):
        for category in self.fm.category_list:
            print_format = '{0}{1}{2}' if '-' not in category else None
            file_count = len(self.fm.category_list_dict[category])
            if file_count > 0:
                self.prompt_for_rename = True if not category.endswith('-') else False
                category_for_print = category.replace('-', '')
                print()
                print('{0} {1} {2} {3} {4} {5}'.format('--',
                                                       category_for_print,
                                                       '-' * (75 - len(category_for_print) - len(str(file_count))),
                                                       str(file_count),
                                                       'Files',
                                                       '-' * 5))
                for fo in self.fm.category_list_dict[category]:
                    if print_format is None:
                        print('{0}{1}'.format(' ' * 3, fo.file_name))
                    else:
                        print(str(print_format).format(fo.file_name.rjust(36, ' '), '  ->  ', fo.new_file_name))
        print()

    def rename(self):
        if self.prompt_for_rename is False:
            print('Nothing to rename.')
            return
        inpt = input('Rename these?... Hit y to rename, or any other key to abort:')
        print()
        if inpt != 'y':
            print('Rename aborted.')
        else:
            for category in self.fm.category_list:
                if len(self.fm.category_list_dict[category]) > 0:
                    for fo in self.fm.category_list_dict[category]:
                        fo.rename()
            print('Rename completed.')


def main():
    try:
        ArgsManager.parse_args()

        # collect_files()
        file_manager = FileManager()
        with ExifToolManager.get_et():
            DirectoryManager().process_directory(ArgsManager.directory, file_manager)

        results_manager = ResultsManager(file_manager)
        results_manager.print_results()
        results_manager.rename()

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()

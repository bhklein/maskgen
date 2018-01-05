import unittest
import os
from maskgen import plugins, image_wrap,exif
import numpy
import tempfile
from tests.test_support import TestSupport



class CompressAsTestCase(TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_gray(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project5.jpg'))
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = self.locateFile('tests/images/test_project5.jpg')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.jpg', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output,format='JPEG')

        args,error = plugins.callPlugin('CompressAs',
                            img_wrapper,
                           filename,
                           filename_output,
                           donor=filename,
                          rotate='yes')
        self.assertEqual(error,None)
        data = exif.getexif(filename)

        args, error = plugins.callPlugin('OutputTIFF',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         donor=filename,
                                         rotate='yes')
        self.assertEqual(error, None)
        data = exif.getexif(filename)

        args, error = plugins.callPlugin('OutputPNG',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         donor=filename,
                                         rotate='yes',
                                         **{'Image Rotated': 'yes'})
        self.assertEqual(error, None)
        self.assertEqual('yes',args['Image Rotated'])
        data = exif.getexif(filename)

        args, error = plugins.callPlugin('OutputBMP',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         donor=filename,
                                         rotate='yes',
                                         **{'Image Rotated':'yes'})
        self.assertEqual(error, None)
        data = exif.getexif(filename)
        self.assertEqual('yes', args['Image Rotated'])

        args, error = plugins.callPlugin('OutputTIFF',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         donor=filename,
                                         **{'Image Rotated': 'yes'})
        self.assertEqual('yes', args['Image Rotated'])
        self.assertEqual(error, None)
        data = exif.getexif(filename)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()

# from PIL import Image as pil

# def crop
#
# https://www.djangosnippets.org/snippets/934/
# http://www.psychicorigami.com/2009/06/20/django-simple-admin-imagefield-thumbnail/
#
# http://djangosaur.tumblr.com/post/422589280/django-resize-thumbnail-image-pil
# https://djangosnippets.org/snippets/224/
# from cStringIO import StringIO
#
# """Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""
# def rescale(data, width, height, force=True):
#
# 	max_width = width
# 	max_height = height
#
# 	input_file = StringIO(data)
# 	img = pil.open(input_file)
# 	if not force:
# 		img.thumbnail((max_width, max_height), pil.ANTIALIAS)
# 	else:
# 		src_width, src_height = img.size
# 		src_ratio = float(src_width) / float(src_height)
# 		dst_width, dst_height = max_width, max_height
# 		dst_ratio = float(dst_width) / float(dst_height)
#
# 		if dst_ratio < src_ratio:
# 			crop_height = src_height
# 			crop_width = crop_height * dst_ratio
# 			x_offset = float(src_width - crop_width) / 2
# 			y_offset = 0
# 		else:
# 			crop_width = src_width
# 			crop_height = crop_width / dst_ratio
# 			x_offset = 0
# 			y_offset = float(src_height - crop_height) / 3
# 		img = img.crop((x_offset, y_offset, x_offset+int(crop_width), y_offset+int(crop_height)))
# 		img = img.resize((dst_width, dst_height), pil.ANTIALIAS)
#
# 	tmp = StringIO()
# 	img.save(tmp, 'JPEG')
# 	tmp.seek(0)
# 	output_data = tmp.getvalue()
# 	input_file.close()
# 	tmp.close()
#
# 	return output_data
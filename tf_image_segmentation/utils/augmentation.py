import tensorflow as tf


def scale_jittering_tensor_with_fixed_size_output(img_tensor,
                                                  annotation_tensor,
                                                  output_shape,
                                                  min_relative_random_scale_change,
                                                  max_realtive_random_scale_change,
                                                  mask_out_number):
    """Returns tensor of a size (output_shape, output_shape, depth) and (output_shape, output_shape, 1).
    The function returns tensor that is of a size (output_shape, output_shape, depth)
    which is randomly scaled by a factor that is sampled from a uniform distribution
    between values [min_relative_random_scale_change, max_realtive_random_scale_change] multiplied
    by the factor that is needed to scale image to the output_shape. When the rescaled image
    doesn't fit into the [output_shape] size, the image is either padded or cropped. Also, the
    function returns scaled annotation tensor of the size (output_shape, output_shape, 1). Both,
    the image tensor and the annotation tensor are scaled using nearest neighbour interpolation.
    This was done to preserve the annotation labels. Be careful when specifying the big sample
    space for the random variable -- aliasing effects can appear. When scaling, this function
    preserves the aspect ratio of the original image. When performing all of those manipulations
    there will be some regions in the output image with blank regions -- the function masks out
    those regions in the annotation using mask_out_number. Overall, the function performs the
    rescaling neccessary to get image of output_shape, adds random scale jitter, preserves
    scale ratio, masks out unneccassary regions that appear.
    
    Parameters
    ----------
    img_tensor : Tensor of size (width, height, depth)
        Tensor with image
    annotation_tensor : Tensor of size (width, height, 1)
        Tensor with respective annotation
    output_shape : Tensor or list [int, int]
        Tensor of list representing desired output shape
    min_relative_random_scale_change : float
        Lower bound for uniform distribution to sample from
        when getting random scaling jitter
    max_realtive_random_scale_change : float
        Upper bound for uniform distribution to sample from
        when getting random scaling jitter
    mask_out_number : int
        Number representing the mask out value.
        
    Returns
    -------
    labels_2d_stacked : Tensor of size (width, height, num_classes).
        Tensor with labels for each pixel.
    """
    
    # tf.image.resize_nearest_neighbor needs
    # first dimension to represent the batch number
    img_batched = tf.expand_dims(img_tensor, 0)
    annotation_batched = tf.expand_dims(annotation_tensor, 0)

    # Convert to int_32 to be able to differentiate
    # between zeros that was used for padding and
    # zeros that represent a particular semantic class
    annotation_batched = tf.to_int32(annotation_batched)

    # Get height and width tensors
    input_shape = tf.shape(img_batched)[1:3]

    input_shape_float = tf.to_float(input_shape)

    scales = output_shape / input_shape_float

    rand_var = tf.random_uniform(shape=[1],
                                 minval=min_relative_random_scale_change,
                                 maxval=max_realtive_random_scale_change)

    final_scale = tf.reduce_min(scales) * rand_var

    scaled_input_shape = tf.to_int32(tf.round(input_shape_float * final_scale))
    
    # Resize the image and annotation using nearest neighbour
    # Be careful -- may cause aliasing.
    
    # TODO: try bilinear resampling for image only
    resized_img = tf.image.resize_nearest_neighbor( img_batched, scaled_input_shape )
    resized_annotation = tf.image.resize_nearest_neighbor( annotation_batched, scaled_input_shape )

    resized_img = tf.squeeze(resized_img, axis=0)
    resized_annotation = tf.squeeze(resized_annotation, axis=0)

    # Shift all the classes by one -- to be able to differentiate
    # between zeros representing padded values and zeros representing
    # a particular semantic class.
    annotation_shifted_classes = resized_annotation + 1

    cropped_padded_img = tf.image.resize_image_with_crop_or_pad( resized_img, output_shape[0], output_shape[1] )

    cropped_padded_annotation = tf.image.resize_image_with_crop_or_pad(annotation_shifted_classes,
                                                                       output_shape[0],
                                                                       output_shape[1])
    
    # TODO: accept the classes lut instead of mask out
    # value as an argument
    annotation_additional_mask_out = tf.to_int32(tf.equal(cropped_padded_annotation, 0)) * (mask_out_number+1)

    cropped_padded_annotation = cropped_padded_annotation + annotation_additional_mask_out - 1
    
    return cropped_padded_img, cropped_padded_annotation
# -*- coding: utf-8 -*-
"""GAN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1a4rWxsB4h9tvfx0XJ6gExzi-Q3tNblYI

# **1. IMPORT DATASET FROM KAGGLE **
"""

!pip install -q kaggle

from google.colab import files

files.upload()

!mkdir ~/.kaggle

!cp kaggle.json ~/.kaggle/

!chmod 600 ~/.kaggle/kaggle.json

!kaggle datasets download -d greg115/abstract-art

from google.colab import drive
drive.mount('/content/drive')

!unzip abstract-art.zip -d "/content/drive/MyDrive/Data_science/abstract-art"

"""# **IMPORT AND MODIFY DATASET**"""

!pip install pillow

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import random
import os
import seaborn as sns
from PIL import Image, ImageOps, ImageFont, ImageDraw

gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

data_path = "/content/drive/MyDrive/Data_science/abstract-art/abstract_art_512"
batch_size = 128
ds = tf.keras.utils.image_dataset_from_directory(
    data_path,
    label_mode = None,
    image_size = (64, 64),
    batch_size = batch_size
)

plt.figure(figsize=(10, 10))
for images in ds.take(1):
  print(images.shape)
  for i in range(9):
    ax = plt.subplot(3, 3, i + 1)
    plt.imshow(images[i].numpy().astype("uint8"))

    plt.axis("off")

for image_batch in ds:
  print(image_batch.shape)
  break

normalization_layer = tf.keras.layers.Rescaling(1./127.5, offset=-1)
normalized_ds = ds.map(lambda t: normalization_layer(t))

image_batch = next(iter(normalized_ds))

# print(np.min(image_batch[0]), np.max(image_batch[0]))

AUTOTUNE = tf.data.AUTOTUNE
normalized_ds = normalized_ds.cache().prefetch(buffer_size=AUTOTUNE)

#  image batch = normalized_data.iter().next()

"""# ***GENERATOR***"""

from tensorflow.python.keras.layers.core import Reshape
import tensorflow
from tensorflow import keras
from keras import Sequential
from keras.layers import Conv2D, Dense, Flatten, Reshape, LeakyReLU, Dropout, Conv2DTranspose

def build_generator():

  model = Sequential()

  # we will convert it into 4x4x1024
  model.add(Dense(4*4*1024, use_bias=False, input_dim=128))
  model.add(tf.keras.layers.BatchNormalization())
  model.add(LeakyReLU(alpha=0.2))
  model.add(Reshape((4, 4, 1024)))

  assert model.output_shape == (None, 4, 4, 1024)  # Note: None is the batch size

  model.add(Conv2DTranspose(512, (5, 5), strides=2, padding='same', use_bias=False))
  assert model.output_shape == (None, 8, 8, 512)
  model.add(tf.keras.layers.BatchNormalization())
  model.add(LeakyReLU(alpha=0.2))

  model.add(Conv2DTranspose(256, (5, 5), strides=2, padding='same', use_bias=False))
  assert model.output_shape == (None, 16, 16, 256)
  model.add(tf.keras.layers.BatchNormalization())
  model.add(LeakyReLU(alpha=0.2))


  model.add(Conv2DTranspose(128, (5, 5), strides=2, padding='same', use_bias=False))
  assert model.output_shape == (None, 32, 32, 128)
  model.add(tf.keras.layers.BatchNormalization())
  model.add(LeakyReLU(alpha=0.2))

  model.add(Conv2DTranspose(3, (5, 5), strides=(2, 2), padding='same', use_bias=False, activation='sigmoid'))
  assert model.output_shape == (None, 64, 64, 3)
  model.add(tf.keras.layers.Activation("tanh"))

  return model

generator = build_generator()
generator.summary()

image_batch[0].shape

img = generator.predict(np.random.randn(4, 128, 1))

img.shape

"""# ***DISCRIMINATOR***"""

def build_discriminator():

  model = Sequential()

  model.add(Conv2D(64, kernel_size=5, strides=2, padding='same', input_shape=(64, 64, 3)))
  model.add(LeakyReLU(alpha=0.2))
  model.add(Dropout(0.1))

  model.add(Conv2D(128, kernel_size=5, strides=2, padding='same'))
  model.add(LeakyReLU(alpha=0.2))
  model.add(Dropout(0.1))

  model.add(Conv2D(256, kernel_size=5, strides=2, padding='same'))
  model.add(LeakyReLU(alpha=0.2))
  model.add(Dropout(0.1))

  model.add(Conv2D(512, kernel_size=5, strides=2, padding='same'))
  model.add(LeakyReLU(alpha=0.2))

  model.add(Flatten())
  model.add(Dense(1, activation='sigmoid'))

  return model

discriminator = build_discriminator()
discriminator.summary()

img.shape

discriminator.predict(img)

"""# ***GAN MODEL***"""

class ArtisticGAN(keras.models.Model):
  def __init__(self, generator, discriminator, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.generator = generator
    self.discriminator = discriminator

    self.batch_size = 128
    self.noise_dim = 128

  def compile(self, g_loss, g_opt, d_loss, d_opt, *args, **kwargs):

    super().compile(*args, **kwargs)

    self.g_loss = g_loss
    self.g_opt = g_opt
    self.d_loss = d_loss
    self.d_opt = d_opt

  def train_step(self, batch):

    real_images = batch
    input_noise = tf.random.normal([self.batch_size, self.noise_dim, 1])
    fake_images = self.generator(input_noise, training=False)

    # train the discriminator

    with tf.GradientTape() as d_tape:

      yhat_real = self.discriminator(real_images, training=True)
      yhat_fake = self.discriminator(fake_images, training=True)

      yhat_realfake  = tf.concat([yhat_real, yhat_fake], axis=0)

      # we set the output that real is 1 and fake as 0
      y_realfake = tf.concat([tf.zeros_like(yhat_real), tf.ones_like(yhat_fake)], axis=0)

      # adding noise to true outputs to cofuse the discriminator

      noise_real = 0.15*tf.random.uniform(tf.shape(yhat_real))
      noise_fake = -0.15*tf.random.uniform(tf.shape(yhat_fake))
      y_realfake += tf.concat([noise_real, noise_fake], axis=0)

      total_d_loss = self.d_loss(y_realfake, yhat_realfake)

    dgrad = d_tape.gradient(total_d_loss, self.discriminator.trainable_variables)
    self.d_opt.apply_gradients(zip(dgrad, self.discriminator.trainable_variables))

    # train generator
    with tf.GradientTape() as g_tape:

      train_input_noise = tf.random.normal([self.batch_size, self.noise_dim, 1])
      generated_imgs = self.generator(train_input_noise, training=True)

      predicted_labels = self.discriminator(generated_imgs, training=False)

      total_g_loss = self.g_loss(tf.zeros_like(predicted_labels), predicted_labels)

    ggrad = g_tape.gradient(total_g_loss, self.generator.trainable_variables)
    self.g_opt.apply_gradients(zip(ggrad, self.generator.trainable_variables))

    return {"d_loss":total_d_loss, "g_loss":total_g_loss}

from keras.optimizers import Adam
from keras.losses import BinaryCrossentropy

g_opt = Adam(learning_rate=0.0001)
d_opt = Adam(learning_rate=0.0001)
g_loss = BinaryCrossentropy()
d_loss = BinaryCrossentropy()

"""# ***CALLBACK***"""

from keras.preprocessing.image import array_to_img
import os
from keras.callbacks import Callback

class ModelMonitor(Callback):
  def __init__(self, num_imgs = 3, latent_dims=128):
    self.num_imgs = num_imgs
    self.latent_dims = latent_dims

  def op_epoch_end(self, epoch, logs=None):
    if epoch%5 ==0:
      latent_vector = tf.random.normal((self.num_imgs, latent_dims, 1))
      generated_imgs = self.model.generator(latent_vector)
      generated_images *= 255
      generated_images.numpy()
      for i in range(self.num_img):
              img = array_to_img(generated_images[i])
              img.save('/content/testing_images/'+f'generated_img_{epoch}_{i}.png')

"""# ***FINALLY TRAIN THE MODEL***"""

model = ArtisticGAN(generator, discriminator)
model.compile(g_loss=g_loss, g_opt=g_opt, d_loss=d_loss, d_opt=d_opt)

hist = model.fit(normalized_ds, epochs=10, callbacks=[ModelMonitor()])

plt.suptitle('Loss')
plt.plot(hist.history['d_loss'], label='d_loss')
plt.plot(hist.history['g_loss'], label='g_loss')
plt.legend()
plt.show()

imgs = generator.predict(tf.random.normal((16, 128, 1)))

fig, ax = plt.subplots(ncols=4, nrows=4, figsize=(10,10))
for r in range(4):
    for c in range(4):
        ax[r][c].imshow(imgs[(r+1)*(c+1)-1])

"""Since only tained for ten epochs it isnt still good enough but it should improve over time as we increase number if epochs to to around 500-100

A basic implementation will get ariund to do the same for creating a tiny shakespear as imspired by **Adrej Karpathy**
"""
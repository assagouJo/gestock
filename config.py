import cloudinary
import cloudinary.uploader
import cloudinary.api
import os

cloudinary.config(
    cloud_name=os.getenv("dmjote21b"),
    api_key=os.getenv("692988672826417"),
    api_secret=os.getenv("C4TcBhw9j8C_T8R6qsFaRAoisn0"),
    secure=True
)

from django.db import models

# Create your models here.

class Pages(models.Model):
    name = models.TextField()
    page = models.TextField()

class Channels(models.Model):
    title = models.TextField()
    RSS = models.URLField()
    # url del sitio original
    url = models.URLField()
    logo = models.URLField()
    last_updated = models.DateTimeField(auto_now=True)
    presentation = models.TextField()
    # numero de noticias que hay en el canal
    nentries = models.TextField()

class News(models.Model):
    title = models.TextField()
    url = models.URLField()
    contenido = models.TextField()
    PubDate = models.TextField()
    presentation = models.TextField()

# Esta tabla relaciona las noticias con el canal al que pertenecen
class News_Channels(models.Model):
    NewId = models.TextField()
    ChannelId = models.TextField()

class User_Conf(models.Model):
    userId = models.TextField()
    user_name = models.TextField()
    journal_title = models.TextField()
    last_updated = models.TextField()

# Tabla con comentarios sobre las revistas
class Comments(models.Model):
    # User que hizo el comentario
    UserId = models.TextField()
    Comment = models.TextField()
    # Username del propietario de la revista
    Users_Journal = models.TextField()

# Tabla con los likes
class likes(models.Model):
    UserId = models.TextField()
    Counter = models.TextField()
    NewId = models.TextField()

# Tabla con el registro de likes por usuario
class user_like(models.Model):
    UserId = models.TextField()
    NewId = models.TextField()

# Esta tabla relaciona las noticias con el usuario al que pertenecen
class New_User(models.Model):
    NewId = models.TextField()
    UserId = models.TextField()
    date = models.TextField()

# Tabla con las configuraciones de color de texto, color de fondo, tamano de texto
class User_Custom(models.Model):
    UserId = models.TextField()
    background = models.TextField()
    font_size = models.TextField()
    color = models.TextField()





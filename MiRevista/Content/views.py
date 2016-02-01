# Create your views here.

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, HttpResponseNotAllowed
from models import Pages
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from Content.models import Pages, Channels, News, News_Channels, User_Conf, New_User, User_Custom, Comments, likes, user_like
from django.contrib.auth.models import User
import datetime

# Import para plantillas
from django.template.loader import get_template
from django.template import Context

# Import para el feed
import feedparser
from bs4 import BeautifulSoup
import urllib2

# Import para manejo de usuarios
from django.contrib.auth import authenticate, login, logout

@csrf_exempt
# Gestiona el recurso '/' el recurso '/user' y el resto
def server(request, resource):
    if do_login_logout(request):
        return HttpResponseRedirect(request.path)

    body = ''
    if request.method == 'GET':
        # Me estan pidiendo el recurso /
        if resource == '':
            body = ''
            journals_list = User_Conf.objects.all().order_by('last_updated')
            for journal in journals_list:
                body = '<div class="post"> ' + \
                           '<h2 class="title"><a href="/' + journal.user_name + '">' + journal.journal_title + '</a></h2>' + \
                           '<div style="clear: both;">&nbsp;</div>' + \
                           '<div class="entry">User: ' + journal.user_name + '</div>' + \
                           '<div class="entry">' + str(journal.last_updated) + '</div>' + \
                       '</div>' + body
            return show_annotated_content(request, body)
        else:
            # Se comprueba si el recurso que me piden coincide con algun /usuario existente
            try:
                user = User.objects.get(username=resource)
            except User.DoesNotExist:
                return HttpResponseNotFound('404 Not Found')

            # se procede a listar las noticias que sigue el usuario
            # Sacamos el id del usuario al que pertenece la revista
            try:
                user = User.objects.get(username=str(resource))
            except User.DoesNotExist:
                return show_annotated_content(request, "Error: User does not found")

            # Nos quedamos solamente con el id de las noticias del usuario al que pertenece la revista
            news = New_User.objects.filter(UserId=user.id)

            for n in reversed(news):
                # Sacamos el canal para concatenar su titulo y su id en la presentacion de la noticia
                new_channel = News_Channels.objects.get(NewId=n.NewId)
                channel = Channels.objects.get(id=new_channel.ChannelId)
                # Sacamos la noticia para concatenar sus campos en la presentacion
                new = News.objects.get(id=str(n.NewId))
                body += concatenate_new_presentation(request, channel.id, channel.title, new.id, new.title, new.contenido, new.url,
                                                     new.PubDate, n.date)

            presentation = '<h3>Comments</h3><div class="post">'
            # Sacamos los comentarios que haya de esa revista y los preparamos en formato html
            comments = Comments.objects.filter(Users_Journal=str(request.path)[1:])
            for n in reversed(comments):
                presentation += '<div class="entry">' + n.Comment + '</div>'
                                
            body += presentation + '</div>'
                 
            # Incluimos en el body, el formulario para comentarios, en caso de que sea un usuario logueado
            if request.user.is_authenticated():
                body += '<form action="" method="post">' + \
                            'Title:</br> <input type="text" name="title"></br>' + \
                            'Comments:</br>' + \
                            '<textarea name="comments" id="comments" rows="8" cols="98">' + \
                            'Hey... say something!' + \
                            '</textarea></br>' + \
                            '<input type="submit" value="Send" />' + \
                        '</form>'

            return show_annotated_content(request, body)

    # Dependiendo de lo que venga en la query haremos una cosa u otra
    elif request.method == 'POST':
        print (str(request.POST))
        # Un user quiere cambiar el titulo de su revista
        if 'newtitle' in request.POST:
            new_title = (str(request.POST)).split("'")[6]
            user_conf = User_Conf.objects.get(user_name=request.user)
            user_conf.journal_title = new_title
            user_conf.save()
            return HttpResponseRedirect(request.path)
        # Un user quiere valorar una noticia
        elif 'like' in str(request.POST):
             print str(request.POST)
             # Por defecto es un like, por tanto se suma 1
             score = 1
             # Sacamos el id de la noticia que se esta valorando
             NewId = (str(request.POST)).split("'")[11]
             # Sacamos el id del user
             user = User.objects.get(username=str(request.user))
             # Comprobamos si es like o dislike, y se sumara +1 o -1 respectivamente al contador
             if 'dislike' in str(request.POST):
                 score = -1
             # Comprobamos si la noticia se ha valorado antes, si no es asi, se crea un nuevo campo
             try:
                 rating = likes.objects.get(NewId=NewId)
             except likes.DoesNotExist:
                 new_rating = likes(UserId=user.id, Counter=score, NewId=NewId)
                 new_rating.save()
                 new_record = user_like(UserId=user.id, NewId=NewId)
                 new_record.save()
                 return HttpResponseRedirect(request.path)
             # Comprobamos si ese usuario ha puntuado esa noticia antes, para evitar que puntue varias veces
             record = user_like.objects.filter(NewId=NewId)
             for n in record:
                 if str(n.UserId) == str(user.id):
                     return HttpResponseRedirect(request.path)

             # Como no ha puntuado antes, sumamos el score y creamos un campo en el registro de likes
             rating.Counter = str(int(rating.Counter) + score)
             rating.save()

             new_record = user_like(UserId=user.id, NewId=NewId)
             new_record.save()
             return HttpResponseRedirect(request.path)
        # Un user ha enviado un comentario
        elif 'comments' in request.POST:
            # sacamos el id del usuario que envia el comentario
            user_name = str(request.user)
            user = User.objects.get(username=user_name)
            title = (str(request.POST)).split("'")[7]
            comment = (str(request.POST)).split("'")[3]
            comment_presentation = '<font size="3"><b>' + user_name + ':</b></font size></br>' + \
                                   '(<b>' + title + '</b>): ' + comment
            # Incluimos el comentario en la tabla Comments
            new_comment = Comments(UserId=user.id, Comment=comment_presentation, Users_Journal=str(request.path)[1:])
            new_comment.save()
            return HttpResponseRedirect(request.path)
        # Un user quiere personalizar el css
        elif 'personalize' in request.POST:
            new_color = (str(request.POST)).split("'")[3]
            new_font = (str(request.POST)).split("'")[7]
            new_back = (str(request.POST)).split("'")[15]
            # Sacamos el ID del user conectado
            user = User.objects.get(username=request.user)
            # Comprobamos si tiene una personalizacion antrior
            # si no, la creamos
            try:
                record = User_Custom.objects.get(UserId=user.id)
            except:
                new = User_Custom(UserId=user.id, background=new_back, font_size=new_font, color=new_color)
                new.save()
                return HttpResponseRedirect(request.path)

            record.background = new_back
            record.font_size = new_font
            record.color = new_color
            record.save()

            return HttpResponseRedirect(request.path)
        # Un user quiere seguir una noticia que se encuentra en una revista
        else:
            # sacamos el link de la noticia y lo usamos como identificador
            new_link = (str(request.POST)).split("'")[3]
            try:
                record = News.objects.get(url=new_link)
            except News.DoesNotExist:
                return show_annotated_content(request, "Error: new's url does not found")

            #sacamos el id del ususario que se encuentra logueado
            try:
                user = User.objects.get(username=str(request.user))
            except User.DoesNotExist:
                return show_annotated_content(request, "Error: User does not found")

            # Comprobamos que el usuario no haya incluido esa noticia anterior mente
            News_list = New_User.objects.filter(UserId=user.id)
            for new in News_list:
                if int(new.NewId) == int(record.id):
                    return HttpResponseRedirect(request.path)

            # Actualizamos la conf del user, si el usuario no existe, se crea su revista
            try:
                user_conf = User_Conf.objects.get(user_name=user.username)
            except User_Conf.DoesNotExist:
                create_user_conf(user.username)
                user_conf = User_Conf.objects.get(user_name=user.username)

            # Actualizazmos el user_conf del usuario
            user_conf.last_updated = str(datetime.datetime.now())
            user_conf.save()

            # incluimos la noticia en la tabla de usuario/noticia
            follow_new = New_User(NewId=record.id, UserId=user.id, date=str(datetime.datetime.now()))
            follow_new.save()
        
            return HttpResponseRedirect(request.path)

    else:
        return HttpResponseNotAllowed('403 METHOD NOT ALLOWED')



@csrf_exempt
# Actualiza o crea la tabla User_Conf con los nuevos usuarios
def create_user_conf(user):
    try:
        user = User.objects.get(username=user)
    except User.DoesNotExist:
        return show_annotated_content(request, 'Error: User does not exist')

    try:
        record = User_Conf.objects.get(user_name=user)
        return show_annotated_content(request, 'Error: User already exist in User_Conf table')
    except User_Conf.DoesNotExist:
        record = User_Conf(userId=user.id,
                           user_name=user.username,
                           journal_title= user.username + "'s Journal",
                           last_updated=str(datetime.datetime.now()))
        record.save()

    return ('Done')


@csrf_exempt
# Loguea o deloguea a un usuario
def do_login_logout(request):
    if request.method == 'POST':
        if 'login' in str(request.POST):
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return (True)
            else:
                return show_annotated_content(request, 'YOUR USERNAME OR YOUR PASS IS INCORRECT')
        elif 'logout' in str(request.POST):
            logout(request)
            return (True)


@csrf_exempt
# Handler para el recurso /canales
def channels(request):
    # Comprobamos si el usuario quiere loguearse o desloguearse
    if do_login_logout(request):
        return HttpResponseRedirect(request.path)

    if request.user.is_authenticated():
        if request.method == 'POST':
            # En el caso de que estemos en /canales
            if request.path == '/canales':
                rss = (str(request.POST)).split("'")[3]
                add_channel(request, rss)
                return HttpResponseRedirect(request.path)
            # En el caso de que estemos en /canales/(numero)
            else:
                # si salta la excepcion es porque no hay nada en el POST
                # y por tanto nos piden actualizar el canal.
                # si no salta la excepcion, entoces es porque
                # nos piden seguir una noticia
                try:
                    action = (str(request.POST)).split("'")[1]
                except IndexError:
                    # sacamos el numero del path
                    num = (request.path).split('/')[2]
                    try:
                        channel = Channels.objects.get(id=num)
                    except Channels.DoesNotExist:
                        return HttpResponseNotFound('404 Not Found')
                    rss = channel.RSS
                    # Esta funcion tambien actualiza los canales
                    add_channel(request, rss)
                    return HttpResponseRedirect(request.path)
                
                # sacamos el link de la noticia y lo usamos como identificador
                new_link = (str(request.POST)).split("'")[3]
                try:
                    record = News.objects.get(url=new_link)
                except News.DoesNotExist:
                    return show_annotated_content(request, "Error: new's url does not found")
    
                #sacamos el id del ususario que se encuentra logueado
                try:
                    user = User.objects.get(username=str(request.user))
                except User.DoesNotExist:
                    return show_annotated_content(request, "Error: User does not found")

                # Contamos el numero de noticias que sigue el user
                n = New_User.objects.filter(UserId=user.id)
                if len(n) == 10:
                    delete_object = New_User.objects.get(id=n[0].id)
                    delete_object.delete()
                    
                # por defecto se incluye la noticia
                action = 'add'

                # comprobamos si la noticia se a incluido, en tal caso, debemos comprobar
                # si la ha incluido el user actual u otro
                new = New_User.objects.filter(NewId=record.id)

                if len(new) > 0:
                    for n in new:
                        if str(n.UserId) == str(user.id):
                            action = 'donotadd'
                            break

                if action == 'add':
                    # Incluimos la noticia a la tabla de noticias seguidas
                    follow_new = New_User(NewId=record.id, UserId=user.id, date=str(datetime.datetime.now()))
                    follow_new.save()

                    # Actualizamos la conf del user, si el usuario no existe, se crea su revista
                    try:
                        user_conf = User_Conf.objects.get(user_name=user.username)
                    except User_Conf.DoesNotExist:
                        create_user_conf(user.username)
                        user_conf = User_Conf.objects.get(user_name=user.username)

                    # Actualizazmos el user_conf del usuario
                    user_conf.last_updated = str(datetime.datetime.now())
                    user_conf.save()

                return HttpResponseRedirect(request.path)
    
        elif request.method == 'GET':
            # En el caso de que estemos en /canales
            if request.path == '/canales':
                body = ''
                Channels_list = Channels.objects.all().order_by('last_updated')
                for channel in reversed(Channels_list):
                    body += channel.presentation

                return show_annotated_content(request, body)

            # En el caso de que estemos en /canales/(numero)
            else:
                # sacamos el numero del path
                num = (request.path).split('/')[2]
                # contador para recorrer la tabla de noticias
                count = 1
                # Sacamos el titulo del canal
                try:
                    channel = Channels.objects.get(id=num)
                    body = '<h2 class="title"><a href="' + channel.url + '">' + channel.title + '</a></h2>' + \
                           '<form name="input" action="" method="POST">' + \
                               '<input class="more" type="submit" value="Update">' + \
                           '</form>' + \
                           '<a href="' + channel.RSS + '">(canal)</a>' + \
                           '<br><br>'
                except Channels.DoesNotExist:
                    return HttpResponseNotFound('404 Not Found')
    

                # mostramos las noticias con el ID del canal
                News_Channel_list = News_Channels.objects.filter(ChannelId=num)
                for New_Channel in reversed(News_Channel_list):
                    new = News.objects.get(id=New_Channel.NewId)
                    body += new.presentation

                return show_annotated_content(request, body)

        else:
            return HttpResponseNotAllowed('405 REQUEST METHOD NOT ALLOWED')

    # En caso de que no haya un user autenticado
    else:
        if request.method == 'POST':
            do_login_logout(request)
            return HttpResponseRedirect(request.path)
        else:
            return show_annotated_content(request, 'Please Login to enjoy this page')
# Add or Update a channel to Channels table
@csrf_exempt
def add_channel(request, url):
    d = feedparser.parse(url)
    nentries = len(d.entries)
    try:
        record = Channels.objects.get(RSS=url)
        record.title = d.feed.title
        record.url = d.feed.link
        record.logo = d.feed.image.url
        record.last_updated = str(datetime.datetime.now())

        # Guardamos las noticias del canal nuevas, n sera el numero de noticias nuevas
        n = add_news(request, d, record.id, record.title, nentries)

        # Sumamos el numero de noticias nuevas a las que ya teniamos
        n += int(record.nentries)
        record.nentries = str(n)

        presentation = concatenate_channel_presentation('<a href="/canales/' + str(record.id) + '">' + d.feed.title + '</a>', d.feed.image.url, 
                                                         record.nentries, record.last_updated)
        record.presentation = presentation
        record.save()

        return 'Channel: "' + d.feed.title + '" updated'
    except Channels.DoesNotExist:
        # Este manejador salta en el caso de que no exista un atributo
        # y por tanto se considera el canal rss como no valido
        try:
            presentation = ''
            record = Channels(title=d.feed.title, RSS=url, url = d.feed.link, logo=d.feed.image.url, last_updated=str(datetime.datetime.now()), 
                              presentation=presentation, nentries=nentries)
            record.save()
            record.presentation = concatenate_channel_presentation('<a href="/canales/' + str(record.id) + '">' + d.feed.title + '</a>',
                                                                    d.feed.image.url, nentries, datetime.datetime.now())
            record.save()
            # Guardamos las noticias del canal
            add_news(request, d, record.id, record.title, nentries)
            return 'Channel: "' + d.feed.title + ' added'
        except AttributeError:
            return 'RSS Channel no valido'

# Concatenate parameters of a channel
def concatenate_channel_presentation(title, logo, nentries, last_updated):
    post =  '<div class="post"> ' + \
                '<h2 class="title">' + title + '</h2>' + \
                '<div style="clear: both;">&nbsp;</div>' + \
                '<img src="' + logo + '"/>' + \
                '<div class="entry">(' + str(nentries) + ' articles)</div>' + \
                '<div class="entry">Last Updated: ' + str(last_updated) + '</div>' + \
            '</div>'
    return(post)

# Add or update news of a channel
@csrf_exempt
def add_news(request, d, channelID, channel_title, nentries):
    n = 0
    for i in reversed(d.entries):
        # noticias incluidas
        # En caso de que la noticia ya este
        # no hace nada, si no esta, salta el manejador
        # y incluye la noticia
        try:
            record = News.objects.get(url=i.link)
        except News.DoesNotExist:
            presentation = concatenate_new_presentation(request, channelID, channel_title, i.id, i.title, i.summary, i.link, i.published, '')
            record = News(title=i.title, url=i.link, contenido=i.summary, PubDate=i.published, presentation=presentation)
            record.save()
            # Ahora incluimos esta noticia en la tabla News_Channels
            newID = News_Channels(NewId=record.id, ChannelId=channelID)
            newID.save()
            n += 1

    return(n)

# devuelve una noticia en HTML para presentarla
def concatenate_new_presentation(request, channelID, channel_title, ID, title, summary, link, PubDate, followed_date):

    div = ''
    rating = ''
    if followed_date != '':
        div = '<div class="entry">Followed date: ' + followed_date + '</div>'
        if request.user.is_authenticated():
            rating = '</br><form name="input" action="" method="POST"></br></br>' + \
                         '<input type="image" src="/templates/images/like.gif" alt="Submit" width="20" height="20"> LIKE ' + \
                         '<input type="hidden" name="like" value="' + str(ID) + '">' + \
                     '</form>' + \
                     '<form name="input" action="" method="POST">' + \
                         '<input type="image" src="/templates/images/dislike.gif" alt="Submit"' + \
                         'width="20" height="20"> DISLIKE' + \
                         '<input type="hidden" name="dislike" value="' + str(ID) + '">' + \
                     '</form>'
            # Comprobamos si alguien ha puntuado esa noticia
            try:
                 print str(ID)
                 score = likes.objects.get(NewId = str(ID))
                 print 'ENCONTRADA'
                 rating += '</br>RAITING ' + str(score.Counter)
            except likes.DoesNotExist:
                 rating += '</br>RAITING +0'

    post = '<div class="post"> ' + \
               '<h2 class="title">' + '<a href="' + link + '">' + title + '</a></h2>' + \
               '<div style="clear: both;">&nbsp;</div>' + \
               '<div class="entry">Publication date: ' + PubDate + '</div>' + \
                div + \
               '<div class="entry">' + summary + '</div>' + \
               '<div class="entry">' + '<a href="/canales/' + str(channelID) + '">(' + channel_title + ')</a></div>' + \
               '<p class="links"><a href="' + link + '" class="more">Read More</a><br>' + \
               '<form name="input" action="" method="POST">' + \
                  '<input type="hidden" name="Follow" value="' + link + '">' + \
                  '<input class="comments" type="submit" value="Follow">' + \
               '</form>' + \
                rating + \
           '</div>'

    return(post)

# Devuelve el form o un mensaje de bienvenida
@csrf_exempt
def loginform(request):
    if request.user.is_authenticated():
        response = '<li>' + \
                       '<p>' + \
                           'Welecome ' + str(request.user) + \
                           '<form name="input" action="" method="POST">' + \
                               '<input type="hidden" name="logout" value="logout">' + \
                               '<input class="comments" type="submit" name="logout" value="Logout">' + \
                           '</form>' + \
                       '</p>' + \
                   '</li>'
    else:
        response = '<li>' + \
                       '<form class="form-1" name="input" action="" method="POST">' + \
                           '<p>Login</p>' + \
                           '<p class="field">' + \
                               '<input type="text" name="username" placeholder="Username">' + \
                               '<i class="icon-user icon-large"></i>' + \
                           '</p>' + \
                               '<p class="field">' + \
                               '<input type="password" name="password" placeholder="Password">' + \
                               '<i class="icon-lock icon-large"></i>' + \
                           '</p>' + \
                           '<p>' + \
                               '<input type="submit" name="login" value="Send"/>' + \
                           '</p>' + \
                       '</form>' + \
                   '</li>'

    return (response)

# Devuelve un formulario para customizar la pagina
@csrf_exempt
def customform(request):
    response = '<li>' + \
                   '<form name="input" action="" method="POST">' + \
                       "<p>Journal's Title</p>" + \
                       '<p class="field">' + \
                           '<input type="text" name="Journal' + "'" + 's Title" placeholder="Journal' + "'" + 's Title">' + \
                           '<i class="icon-user icon-large"></i>' + \
                       '</p>' + \
                       '<p>' + \
                           '<input type="submit" name="newtitle" value="Change"/>' + \
                       '</p>' + \
                   '</form>' + \
                   '<br>' + \
                   '<form name="input" action="" method="POST">' + \
                       "<p>Journal's Customizer</p>" + \
                       '<p class="field">' + \
                           '<input type="text" name="background" placeholder="background">' + \
                           '<i class="icon-lock icon-large"></i>' + \
                       '</p>' + \
                       '<p class="field">' + \
                           '<input type="text" name="font" placeholder="font">' + \
                           '<i class="icon-lock icon-large"></i>' + \
                       '</p>' + \
                       '<p class="field">' + \
                           '<input type="text" name="color" placeholder="color">' + \
                           '<i class="icon-lock icon-large"></i>' + \
                       '</p>' + \
                       '<p>' + \
                           '<input type="submit" name="personalize" value="Change"/>' + \
                       '</p>' + \
                   '</form>' + \
               '</li>'

    return (response)

@csrf_exempt
# Renderiza el css con valores dinamicos
def customvalues(request):
    # Sacamos el id del usuario
    user = User.objects.get(username=request.user)
    # Sacamos los campos de personalizacion del usuario
    values = User_Custom.objects.get(UserId=user.id)
    back = values.background
    font_size = values.font_size
    color = values.color

    template = get_template("defaultdyn.css")

    context = Context({'bannerbackground': back,
                       'sidebarbackground': back,
                       'menubackground': back,
                       'footerbackground': back,
                       'sidebarfontsize': font_size,
                       'menufontsize': font_size,
                       'footerfontsize': font_size,
                       'sidebarfontcolor': color,
                       'menufontcolor': color,
                       'footerfontcolor': color})

    return HttpResponse(template.render(context), content_type='text/css')
    
# Comprueba como hay que rencerizar el css
def cssrend(request):
    if request.user.is_authenticated():
        user = User.objects.get(username=request.user)
        try:
            record = User_Custom.objects.get(UserId=user.id)
            css = 'dynamic'
        except User_Custom.DoesNotExist:
            css = 'estatic'
    else:
        css = 'estatic'

    return (css)


@csrf_exempt
# Coprueba si hay un usuario logueado viendo la pag. de su revista
# y si lo hay, devuelve el formulario del customizer
def customformselected(request):
    if request.user.is_authenticated():
        if (str(request.path)[1:] == str(request.user)):
            return customform(request)
        else:
            return ''
    else:
        return ''

@csrf_exempt
# Comprueba si estamos en la pagina de una revista de usuario y devuelve el html
# del boton de RSS
def journalpage(request):
    resource = (str(request.path)[1:])
    if str(request.path) == '/':
        return '<li><a href="/rss" target="_blank">RSS</a></li>'
    try:
        user = User.objects.get(username=resource)
        return '<li><a href="' + str(request.path) + '/rss" target="_blank">RSS</a></li>'
    except User.DoesNotExist:
        return ''



@csrf_exempt
# Prepara una noticia para ser presentada en xml
def concatenate_xml_new(title, content, link, pubdate):

    new = '<item>' + \
              '<title>' + title + '</title>' + \
              '<link>'+ link + '</link>' + \
              '<pubDate>' + pubdate + '</pubDate>' + \
              '<description><![CDATA[' + content + ']]></description>' + \
                '<slash:comments>0</slash:comments>' + \
          '</item>'

    return(new)

@csrf_exempt
# Renderiza el fichero xml dependiendo de la revista de usuario
def xmlrender(request):
    template = get_template("rss.xml")
    if str(request.path) == '/rss':
        title = 'My Journal'
        link = 'http://localhost:1234/'
        last_updated = ''
        body = ''
        # se procede a listar las revistas de la base de datos
        user = User.objects.all()
        for n in reversed(user):
            print n.username
            try:
                user_conf = User_Conf.objects.get(user_name=n.username)
                body += concatenate_xml_new(user_conf.journal_title, '', 'http://localhost:1234/' + n.username, str(user_conf.last_updated))
            except User_Conf.DoesNotExist:
                body += ''

        context = Context({'title': title,
                           'link': link,
                           'last_updated': last_updated,
                           'news': body})
        return HttpResponse(template.render(context))
    else:
        # Sacamos el nombrede usuario al que pertenece el rss de la revista
        username = (str(request.path)).split('/')[1]

        # Sacamos el titulo de la revista
        user_conf = User_Conf.objects.get(user_name=username)
        title = user_conf.journal_title
        link = '/' + username
        last_updated = user_conf.last_updated

        # se procede a listar las noticias que sigue el usuario
        # Sacamos el id del usuario al que pertenece la revista
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return show_annotated_content(request, "Error: User does not found")

        # Nos quedamos solamente con el id de las noticias del usuario al que pertenece la revista
        news = New_User.objects.filter(UserId=user.id)

        body = ''
        for n in reversed(news):
            # Sacamos el canal para concatenar su titulo y su id en la presentacion de la noticia
            new_channel = News_Channels.objects.get(NewId=n.NewId)
            channel = Channels.objects.get(id=new_channel.ChannelId)
            # Sacamos la noticia para concatenar sus campos en la presentacion
            new = News.objects.get(id=str(n.NewId))
            body += concatenate_xml_new(new.title, new.contenido, new.url, new.PubDate)

        context = Context({'title': title,
                           'link': link,
                           'last_updated': last_updated,
                           'news': body})

    return HttpResponse(template.render(context))

@csrf_exempt
# Contenido del menu ayuda
def help(request):
    if do_login_logout(request):
        return HttpResponseRedirect(request.path)

    content = '<div class="post"> ' + \
                  '<h2 class="title">Help</h2>' + \
                  '<div style="clear: both;">&nbsp;</div>' + \
                  '<h3>Login</h3>' + \
                  '</br>' + \
                  '<div class="entry">Es necesario loguearse para poder acceder a contenidos como: canales,' + \
                  'personalizacion de CSS, revista de usuario, personalizacion del titulo de la revista, comentar en revistas, ' + \
                  'puntuar noticias de revistas.</div>' + \
                  '<h3>Pagina Principal (Journals)</h3>' + \
                  '</br>' + \
                  '<div class="entry">En esta seccion se muestran las distintas revistas de los usuarios registrados.' + \
                  ' Ademas, desde aqui tambien podremos acceder al canal RSS de la pagina principal, donde tendremos los titulos de las' + \
                  ' revistas de los usuarios, como enlaces a las mismas en la aplicacion</div>' + \
                  "<h3>User's Journal</h3>" + \
                  '</br>' + \
                  '<div class="entry">Aqui podremos acceder a la revista de un usuario concreto. Vemos las noticias que ha incluido' + \
                  ' (hasta un maximo de 10 noticias), las cuales podremos seguir pinchando en el boton "Follow".' + \
                  '</br>Si estamos logueados, podermos comentar sobre la revista y tambien podremos puntuar cada noticia de la revista.' + \
                  '</br>Si estamos logueados y ademas somos el propietario de la revista, podremos personalizar los siguentes campos:' + \
                  ' Titulo de la revista, color de fondo (menu,sidebar,footer), font-size (menu,sidebar,footer) y ' + \
                  ' color de letra (menu,sidebar,footer)</p></div>' + \
                  "<h3>User's RSS</h3>" + \
                  '</br>' + \
                  '<div class="entry">Canal RSS de la revista del usuario</div>' + \
                  '<h3>Channels</h3>' + \
                  '</br>' + \
                  '<div class="entry">En esta seccion se muestran los distintos canales incluidos en la web junto con la informacion:' + \
                  'Titulo de Canal, numero de articulos almacenados de ese canal y fecha de ultima actualizacion.' + \
                  '</br>Por otro lado, si entramos en la pagina del canal, se mostraran todas las noticias almacenadas de ese canal,' + \
                  'junto con la informacion: Titulo de la noticia, fecha de publicacion, contenido, y un boton para seguir esa noticia e' + \
                  'incluirla en nuestra revista personal' + \
                  'Ademas, se permite incluir canales rss de otras webs mediante el formulario que aparece en el sidebar.</div>' + \
              '</div>'

    return show_annotated_content(request, content)
           
@csrf_exempt
# Renderiza el fichero html dependiendo de la pag. en la que se encuentre
def show_annotated_content(request, content):
    template = get_template("index.html")
    login_info = loginform(request)
    if request.user.is_authenticated():
        login_menu = login_info
        form = ''
        if request.path == '/canales':
            rss_form = '<h2>Add a new Channel</h2>' + \
                       '<ul>' + \
                           '<form name="input" action="" method="POST">' + \
                           'RSS: <input type="text" name="rss">' + \
                           '<input type="submit" value="Send">' + \
                           '</form>' + \
                       '</ul>'
        else:
            rss_form = ''
    else:
        login_menu = ''
        form = login_info
        rss_form = ''

    # Comprobamos si estamos en una pagina de usuario y de estarlo, renderizamos el boton de RSS
    rss_button = journalpage(request)

    # Comprobamos que si estamos en una pagina de usuario, pertenece al usuario conectado
    custom_form = customformselected(request)

    # Dependiendo del codigo html que incluya, se renderiza dinamicamente o se llama al css estatico
    if cssrend(request) == 'dynamic':
        css = '<link href="css/default.css" rel="stylesheet" type="text/css" media="screen" />' + \
              '<link href="css/defaultdyn.css" rel="stylesheet" type="text/css" media="screen" />'
    else:
        css = '<link href="css/default.css" rel="stylesheet" type="text/css" media="screen" />'


    return HttpResponse(template.render(Context({'css': css,
                                                 'rss': rss_button,
                                                 'content': content,
                                                 'form': form,
                                                 'login_menu': login_menu,
                                                 'rss_form': rss_form,
                                                 'customform': custom_form})))

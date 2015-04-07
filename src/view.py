#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, GLib
from _thread import start_new_thread

from lollypop.define import Objects, Navigation
from lollypop.playlists import PlaylistsManagerWidget, PlaylistEditWidget
from lollypop.devicemanager import DeviceManagerWidget
from lollypop.view_widgets import AlbumDetailedWidget, AlbumWidget
from lollypop.view_widgets import PlaylistWidget
from lollypop.utils import translate_artist_name

# Container for a view
class ViewContainer(Gtk.Stack):
    def __init__(self, duration):
        Gtk.Stack.__init__(self)
        self._duration = duration
        # Don't pass resize request to parent
        self.set_resize_mode(Gtk.ResizeMode.QUEUE)
        self.set_transition_duration(duration)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.show()

    """
        Clean view
        @param view as View
    """
    def clean_view(self, view):
        if view and not isinstance(view, DeviceView):
            view.stop()
            # Delayed destroy as we may have an animation running
            # Gtk.StackTransitionType.CROSSFADE
            GLib.timeout_add(self._duration,
                             self._delayedclean_view,
                             view)

#######################
# PRIVATE             #
#######################
    """
        Clean view
        @param valid view as View
    """
    def _delayedclean_view(self, view):
        view.remove_signals()
        view.destroy()


# Playlist view used to manage playlists
class PlaylistManageView(Gtk.Bin):
    """
         @param object id as int
         @param genre id as int
         @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        Gtk.Bin.__init__(self)
        self._widget = PlaylistsManagerWidget(object_id,
                                              genre_id,
                                              is_album,
                                              self)
        self._widget.show()
        self.add(self._widget)

    def populate(self):
        self._widget.populate()

    def remove_signals(self):
        pass

    def stop(self):
        pass

# Playlist view used to edit playlists
class PlaylistEditView(Gtk.Bin):
    """
         @param playlist name as str
         @param width as int
    """
    def __init__(self, playlist_name, width):
        Gtk.Bin.__init__(self)
        self._widget = PlaylistEditWidget(playlist_name, width, self)
        self._widget.show()
        self.add(self._widget)

    def populate(self):
        self._widget.populate()

    def remove_signals(self):
        pass

    def stop(self):
        pass


# Playlist synchronisation view
class DeviceView(Gtk.Bin):
    """
         @param device as Device
         @param progress as Gtk.ProgressBar
    """
    def __init__(self, device, progress):
        Gtk.Bin.__init__(self)
        self._widget = DeviceManagerWidget(device, progress, self)
        self._widget.show()
        self.add(self._widget)

    def populate(self):
        self._widget.populate()

    def is_syncing(self):
        return self._widget.is_syncing()

    def remove_signals(self):
        pass

    def stop(self):
        pass


#######################
# PRIVATE             #
#######################


# Generic view
class View(Gtk.Grid):

    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self._current_signal = Objects.player.connect("current-changed",
                                                      self._on_current_changed)
        self._cover_signal = Objects.player.connect("cover-changed",
                                                    self._on_cover_changed)
        # Stop populate thread
        self._stop = False

        self._viewport = Gtk.Viewport()
        self._viewport.set_property("valign", Gtk.Align.START)

    """
        Add widget to main viewport
        @param widget as Gtk.Widget
        @param height as int
    """
    def set_main_widget(self, widget, height=None):
        scrolledWindow = Gtk.ScrolledWindow()
        if height is None:
            scrolledWindow.set_vexpand(True)
            scrolledWindow.set_hexpand(True)
        else:
            scrolledWindow.set_min_content_height(250)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.add(self._viewport)
        self._viewport.show()
        scrolledWindow.show()
        self.add(scrolledWindow)
        self._viewport.add(widget)

    """
        Remove signals on player object
    """
    def remove_signals(self):
        if self._current_signal:
            Objects.player.disconnect(self._current_signal)
            self._current_signal = None
        if self._cover_signal:
            Objects.player.disconnect(self._cover_signal)
            self._cover_signal = None


#######################
# PRIVATE             #
#######################
    """
        Current song changed
        Update context and content
        @param player as Player
    """
    def _on_current_changed(self, player):
        self._update_content(player)
        self._update_context(player)

    """
        Update album cover in view
        Do nothing here
    """
    def _on_cover_changed(self, widget, album_id):
        pass

    """
        Update content view
        Do nothing here
    """
    def _update_content(self, player):
        pass

    """
        Update context view
        Do nothing here
    """
    def _update_context(self, player):
        pass

    """
        Stop populate thread
    """
    def stop(self):
        self._stop = True


# Artist view is a vertical grid with album songs widgets
class ArtistView(View):
    """
        Init ArtistView ui with a scrolled grid of AlbumDetailedWidget
        @param artist id as int
        @param show_artist_details as bool
    """
    def __init__(self, artist_id, show_artist_details):
        View.__init__(self)
        self._artist_id = artist_id
        self._signal_id = None

        if show_artist_details:
            builder = Gtk.Builder()
            builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
            self.attach(builder.get_object('ArtistView'),0, 0, 1, 1)
            artist_name = Objects.artists.get_name(artist_id)
            artist_name = translate_artist_name(artist_name)
            builder.get_object('artist').set_label(artist_name)

        self._show_menu = show_artist_details

        self._albumbox = Gtk.Grid()
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self.set_main_widget(self._albumbox)

        self.show()

    """
        Populate the view, can be threaded
        @param navigation id as int
    """
    def populate(self, navigation_id):
        sql = Objects.db.get_cursor()
        if self._artist_id == Navigation.COMPILATIONS:
            albums = Objects.albums.get_compilations(navigation_id,
                                                     sql)
        else:
            albums = Objects.albums.get_ids(self._artist_id,
                                            navigation_id,
                                            sql)
        GLib.idle_add(self._add_albums, albums, navigation_id)
        sql.close()

    """
        Stop populating
    """
    def stop(self):
        View.stop(self)
        for child in self._albumbox.get_children():
            child.stop()
            child.destroy()
#######################
# PRIVATE             #
#######################
    """
        Update album cover in view
        @param album id as int
    """
    def _on_cover_changed(self, widget, album_id):
        for widget in self._albumbox.get_children():
            widget.update_cover(album_id)

    """
        Update the content view
        @param player as Player
    """
    def _update_content(self, player):
        if self._albumbox:
            for widget in self._albumbox.get_children():
                widget.update_playing_track(player.current.id)

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
        @param genre id as int
    """
    def _add_albums(self, albums, genre_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        if len(albums) > 0 and not self._stop:
            widget = AlbumDetailedWidget(albums.pop(0),
                                         genre_id,
                                         self._show_menu,
                                         size_group)
            widget.show()
            start_new_thread(widget.populate, ())
            self._albumbox.add(widget)
            if widget.eventbox:
                window = widget.eventbox.get_window()
                if window:
                    window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))
            GLib.idle_add(self._add_albums, albums,
                          genre_id, priority=GLib.PRIORITY_LOW)
        else:
            self._stop = False


# Album view is a flowbox of albums widgets with album name and artist name
class AlbumView(View):
    """
        Init album view ui with a scrolled flow box and a scrolled context view
        @param navigation id as int
    """
    def __init__(self, navigation_id):
        View.__init__(self)
        self._album_id = None
        self._genre_id = navigation_id
        self._albumsongs = None
        self._context_widget = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect("child-activated", self._on_album_activated)
        self._albumbox.set_max_children_per_line(100)
        self._albumbox.show()

        self.set_main_widget(self._albumbox)

        self._context = ViewContainer(500)

        separator = Gtk.Separator()
        separator.show()
        
        self.add(separator)
        self.add(self._context)
        self.show()

    """
        Populate albums, thread safe
        @param navigation id as int
    """
    def populate(self, navigation_id):
        sql = Objects.db.get_cursor()
        if self._genre_id == Navigation.ALL:
            albums = Objects.albums.get_ids(None, None, sql)
        elif self._genre_id == Navigation.POPULARS:
            albums = Objects.albums.get_populars(sql)
        elif self._genre_id == Navigation.COMPILATIONS:
            albums = Objects.albums.get_compilations(navigation_id,
                                                     sql)
        else:
            albums = Objects.albums.get_ids(None, self._genre_id, sql)
        GLib.idle_add(self._add_albums, albums)
        sql.close()

#######################
# PRIVATE             #
#######################
    """
        Update album cover in view
        @param widget as unused, album id as int
    """
    def _on_cover_changed(self, widget, album_id):
        if self._context_widget:
            self._context_widget.update_cover(album_id)
        for child in self._albumbox.get_children():
            for widget in child.get_children():
                widget.update_cover(album_id)

    """
        Update the context view
        @param player as Player
    """
    def _update_context(self, player):
        if self._context_widget:
            self._context_widget.update_playing_track(player.current.id)

    """
        populate context view
        @param album id as int
    """
    def _populate_context(self, album_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        old_view = self._context.get_visible_child()
        self._context_widget = AlbumDetailedWidget(album_id,
                                                   self._genre_id,
                                                   True,
                                                   size_group)
        start_new_thread(self._context_widget.populate, ())
        self._context_widget.show()
        view = View()
        view.set_main_widget(self._context_widget, 250)
        view.show()
        self._context.add(view)
        self._context.set_visible_child(view)
        self._context.clean_view(old_view)

    """
        Show Context view for activated album
        @param flowbox, children
    """
    def _on_album_activated(self, flowbox, child):
        if self._album_id == child.get_child().get_id():
            if Objects.settings.get_value('auto-play'):
                Objects.player.play_album(self._album_id)
            else:
                self._album_id = None
                self._context.hide()
        else:
            self._album_id = child.get_child().get_id()
            self._populate_context(self._album_id)
            self._context.show()
            self._context_widget.eventbox.get_window().set_cursor(
                                            Gdk.Cursor(Gdk.CursorType.HAND1))

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
    """
    def _add_albums(self, albums):
        if len(albums) > 0 and not self._stop:
            widget = AlbumWidget(albums.pop(0))
            widget.show()
            self._albumbox.insert(widget, -1)
            GLib.idle_add(self._add_albums, albums, priority=GLib.PRIORITY_LOW)
        else:
            self._stop = False


# Playlist view is a vertical grid with album's covers
class PlaylistView(View):
    """
        Init PlaylistView ui with a scrolled grid of PlaylistWidgets
        @param playlist name as str
        @param parent as Gtk.Widget
    """
    def __init__(self, playlist_name, parent):
        View.__init__(self)
        self._parent = parent
        self._playlist_name = playlist_name
        self._signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistView.ui')
        builder.get_object('title').set_label(playlist_name)
        self._header = builder.get_object('header')
        builder.connect_signals(self)

        self._edit_btn = builder.get_object('edit_btn')
        self._back_btn = builder.get_object('back_btn')
        self._title = builder.get_object('title')

        self._playlist_widget = PlaylistWidget(playlist_name)
        self._playlist_widget.show()

        self.add(builder.get_object('PlaylistView'))
        self.set_main_widget(self._playlist_widget)

    """
        Populate view with tracks from playlist
        Thread safe
    """
    def populate(self):
        sql = Objects.db.get_cursor()
        tracks = Objects.playlists.get_tracks_id(self._playlist_name, sql)
        mid_tracks = int(0.5+len(tracks)/2)
        self._playlist_widget.populate_list_one(tracks[:mid_tracks],
                                                1)
        self._playlist_widget.populate_list_two(tracks[mid_tracks:],
                                                mid_tracks + 1)

    """
        Return playlist name
        @return name as str
    """
    def get_name(self):
        return self._playlist_name

    """
        Do show, connect signals
    """
    def do_show(self):
        self._signal_id = Objects.playlists.connect("playlist-changed",
                                                    self._update_view)
        View.do_show(self)

    """
        Do hide, disconnect signals
    """
    def do_hide(self):
        if self._signal_id:
            Objects.playlists.disconnect(self._signal_id)
            self._signal_id = None
        View.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Update tracks widgets
        @param manager as PlaylistsManager
        @param playlist name as str
    """
    def _update_view(self, manager, playlist_name):
        if playlist_name == self._playlist_name:
            self._playlist_widget.clear()
            start_new_thread(self.populate, ())

    """
        Edit playlist
        @param button as Gtk.Button
        @param playlist name as str
    """
    def _on_edit_btn_clicked(self, button):
        window = self._parent.get_toplevel()
        window.show_playlist_editor(self._playlist_name)

    """
        Update the content view
        @param player as Player
    """
    def _update_content(self, player):
        self._playlist_widget.update_playing_track(player.current.id)

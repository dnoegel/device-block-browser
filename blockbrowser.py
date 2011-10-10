#!/usr/bin/env python2
# coding:utf-8

import pygtk
pygtk.require('2.0')
import gtk, gobject, cairo
import os
import random
import math
import subprocess

import struct

BOX_W = 8
BOX_H = 8
MARGIN = 1

class NotFoundException(Exception):
    pass
    
class NoInode(Exception):
    pass
    
class NoPath(Exception):
    pass
    
def get_block_info(block, device):
    """Get inode and path for a given block"""
    
    cmd_inode = "echo -n icheck {block} | debugfs {device}".format(block=block, device=device)
    p = subprocess.Popen(cmd_inode, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    inode = None
    for line in p.stdout:
        if line.startswith(str(block)):
            inode = line.split(None, 1)[1].strip()
            if inode.startswith("<"):
                raise NotFoundException
            
    if inode:
        cmd_name = "echo -n ncheck {inode}| debugfs {device}".format(inode=inode, device=device)
        p = subprocess.Popen(cmd_name, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout:
            if line.startswith(str(inode)):
                path = line.split(None, 1)[1].strip()
                if path.startswith("<"):
                    raise NotFoundException
                return inode, path
                
        raise NoPath(p.stdout.read())
    else:
        raise NoInode(p.stdout.read())
            
    
    cmd_name = "echo -n ncheck {inode}| debugfs {device}".format(inode, device)

class zero_one_scheme_file(object):
    """Wraps a 0/1 scheme file in order to be able to seek and read it
    without having to (re)open it each time"""
    
    def __init__(self, fl):
        
        self.handle = open(fl, "r")
        
        self.struct_format = "16piii"
        self.struct_len = 28
        
        infos = struct.unpack(self.struct_format, self.handle.read(self.struct_len))
        self.device = infos[0]
        self.block_size = infos[1]
        self.free_blocks = infos[3]
        
        #~ self.handle.seek(0,2)
        self.length = infos[2]#self.handle.tell()
        
    def get_block(self, num):
        self.handle.seek(num+self.struct_len)
        return self.handle.read(1)

class MyArea(gtk.DrawingArea):

    # Draw in response to an expose-event
    __gsignals__ = { "expose-event": "override" }

    def __init__(self, scheme_file):
        gtk.DrawingArea.__init__(self)
        
        self.connect('size-allocate', self.size_allocate_cb)
        self.scheme_file = scheme_file
        
        self.add_events(gtk.gdk.BUTTON_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK |gtk.gdk.BUTTON_RELEASE_MASK)
        self.connect("button-release-event", self.button_release_cb)
        
        gobject.signal_new('block-clicked', MyArea, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,(int,))
        gobject.signal_new('per-row-changed', MyArea, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,(int,))
        
        #~ self.set_size_request(700, 999999999)
    
    def button_release_cb(self, widget, event):
        """Emit "block-clicked"-signal, when user clicks on a block"""
        
        x, y = event.x, event.y
        
        w, h = self.window.get_size()
        per_row = math.floor(float(w-MARGIN)/(BOX_W+MARGIN))
        
        # fit to grid
        x = int(math.floor((x)/float(BOX_W+MARGIN))*(BOX_W+MARGIN))+MARGIN
        y = int(math.floor((y)/float(BOX_H+MARGIN))*(BOX_H+MARGIN))+MARGIN
        # convert pixels to position in squares
        xpos = (x -MARGIN) / (BOX_W+MARGIN)
        ypos = (y -MARGIN) / (BOX_H+MARGIN)
        
        ## convert position into sequential block for the
        # zero/one scheme file
        num = int((ypos*per_row)+xpos)
        if num >= self.scheme_file.length:
            return
        b = self.scheme_file.get_block(num)
        
        self.emit("block-clicked", num)
    
    def size_allocate_cb(self, widget, allocation):
        """Recompute size if the allocation changed"""
        
        w, h = allocation.width, allocation.height
        per_row = math.floor(float(w-MARGIN)/(BOX_W+MARGIN))
        rows_needed = math.ceil(self.scheme_file.length/per_row)
        self.set_size_request(700, int(rows_needed*(BOX_H+MARGIN))+MARGIN)
        
        self.emit("per-row-changed", per_row)
        
        print "Now showing {0} blocks ({1} kB) per row".format(per_row, per_row*self.scheme_file.block_size/1024.0)
    
    def do_expose_event(self, event):
        """Handle expose events and redraw"""
        
        #~ x, y = event.area.x, event.area.y
        #~ print event.area
        w, h = self.window.get_size()
        


        # Create the cairo context
        cr = self.window.cairo_create()
        #~ print event.area
        # Restrict Cairo to the exposed area; avoid extra work
        cr.rectangle(event.area.x, event.area.y,
                event.area.width, event.area.height)
        #~ cr.clip()
        
        ## needed?
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        
        self.draw(cr, event)

    def draw(self, cr, event):
        """do the actual drawing"""
        
        ## get event area
        x, y = event.area.x, event.area.y
        w, h = event.area.width, event.area.height
        
        ## calculate max number of blocks per row
        width, height = self.window.get_size()
        per_row = math.floor(float(width-MARGIN)/(BOX_W+MARGIN))

        # Fill the background 
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        ## Fit event-coords to the grid
        x = int(math.floor((x)/float(BOX_W+MARGIN))*(BOX_W+MARGIN))+MARGIN
        y = int(math.floor((y)/float(BOX_H+MARGIN))*(BOX_H+MARGIN))+MARGIN
        
        ## Iter over the event area and draw blocks
        for xx in xrange(x,x+w+BOX_W, BOX_W+MARGIN):
            for yy in xrange(y,y+h+BOX_H, BOX_H+MARGIN):
                # convert pixels to position in squares
                xpos = (xx -MARGIN) / (BOX_W+MARGIN)
                ypos = (yy -MARGIN) / (BOX_H+MARGIN)
                
                # jump to the next loop if position gets to high
                if xpos+1 > per_row:
                    continue
                
                ## convert position into sequential block for the
                # zero/one scheme file
                num = int((ypos*per_row)+xpos)
                b = self.scheme_file.get_block(num)
                #~ print "!{0}!".format(b)
                ## Invalid read (e.g. after EOF)
                if b == " " or b == "":
                    continue
                ## Used block
                elif int(b) == 1:
                    cr.set_source_rgb(1, 0, 0)
                ## Free block
                else:
                    cr.set_source_rgb(0, 1, 0)
                cr.rectangle(xx, yy, BOX_W, BOX_H)
                cr.fill()
                #~ cr.stroke()

class GUI(object):
    def __init__(self):
        self.scheme_file = zero_one_scheme_file("sda3_1.01")
        
        self.window = gtk.Window()
        self.window.set_title("Block usage browser")
        
        self.table = gtk.Table()
        
        self.sw = gtk.ScrolledWindow()

        self.hadj = self.sw.get_hadjustment()
        self.vadj = self.sw.get_vadjustment()

        self.area = MyArea(self.scheme_file)
        self.area.connect("block-clicked", self.block_clicked_cb)
        self.area.connect("per-row-changed", self.per_row_changed_cb)
        
        
        self.sw.add_with_viewport(self.area)
        
        self.table.attach(self.sw, 0, 6, 0, 1, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.EXPAND|gtk.FILL)
        
        #~ b = gtk.Button("+")
        #~ b.connect("clicked", self.button_clicked_cb, "+")
        #~ self.table.attach(b, 0, 1, 1, 2, xoptions=gtk.SHRINK|gtk.FILL, yoptions=gtk.SHRINK|gtk.FILL)
        #~ b = gtk.Button("-")
        #~ b.connect("clicked", self.button_clicked_cb, "-")
        #~ self.table.attach(b, 0, 1, 2, 3, xoptions=gtk.SHRINK|gtk.FILL, yoptions=gtk.SHRINK|gtk.FILL)

        scale = gtk.HScale()
        scale.set_digits(0)
        adj = gtk.Adjustment(value=BOX_W, lower=1, upper=21, step_incr=1, page_incr=1, page_size=1)
        scale.set_adjustment(adj)
        self.table.attach(scale, 0, 1, 1, 2, xoptions=gtk.SHRINK|gtk.FILL, yoptions=gtk.SHRINK|gtk.FILL)
        scale.connect("value-changed", self.value_changed_cb)

        self.lbl_info = gtk.Label()
        
        self.table.attach(self.lbl_info, 5, 6, 1, 2, xoptions=gtk.SHRINK|gtk.FILL, yoptions=gtk.SHRINK|gtk.FILL)

        #~ self.hadj.connect('value-changed', self.adjustmend_changed_cb, True)
        #~ self.vadj.connect('value-changed', self.adjustmend_changed_cb, False)

        self.window.add(self.table)
        self.window.set_default_size(800, 600)
        
        
        self.window.show_all()
    

    #
    # CBs
    #
    def per_row_changed_cb(self, widget, per_row):
        self.lbl_info.set_markup("Block size:     {0}\nTotal Blocks:   {1}\nkB per Row:    {2}".format(self.scheme_file.block_size, self.scheme_file.length, per_row*self.scheme_file.block_size/1024.0))
        
    def value_changed_cb(self, widget):
        global BOX_W, BOX_H
        BOX_W = BOX_H = int(widget.get_value())
        self.area.window.invalidate_rect(gtk.gdk.Rectangle(0,0,self.area.allocation.width, self.area.allocation.height), True) 
        self.area.window.process_updates(True) 
        #~ self.area.set_allocation(self.area.get_allocation())
        self.area.queue_resize()
        
    def block_clicked_cb(self, widget, block):
        if os.geteuid() != 0:
            dia =  gtk.MessageDialog(self.window,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
            dia.set_markup("Error")
            dia.format_secondary_markup("You need to run this script with root privelegs in order to get infos for the selected block")
            dia.run()
            dia.destroy()
            return
        
        dia =  gtk.MessageDialog(self.window,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        dia.set_markup("Getting block infos")
        dia.format_secondary_markup("This might take a few seconds")
        dia.show_all()
        dia.queue_draw()
        while gtk.events_pending():
            gtk.main_iteration(False)

        try:
            inode, path =  get_block_info(block, self.scheme_file.device)
            dia.destroy()
            dia =  gtk.MessageDialog(self.window,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_OK)
            dia.set_markup("Block infos")
            dia.format_secondary_markup("Block: {0}\nInode: {1}\nPath {2}".format(block, inode, path))
            dia.run()
            dia.destroy()
        except (NotFoundException, NoInode, NoPath):
            dia.destroy()
                   
if __name__ == "__main__":
    GUI()
    gtk.main()


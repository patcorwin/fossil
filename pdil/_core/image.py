from __future__ import absolute_import, division, print_function

import collections

from ..vendor.Qt import QtGui, QtWidgets
from ..vendor.Qt.QtCore import QPoint

import math


__all__ = [
    'autoCropContent',
    'identifyContent',
    'disperse',
    'grab',
    'grabTable',
    'grabTree',
]



def autoCropContent(img, chroma=None, padding=0, keepRatio=True):
    '''
    Crop an image to just contain pixels that aren't the chroma key.  Optionally
    keep the same image ratio and pad the edges.
    
    Good for trimming larger images into thumbnails/icons
    
    :chroma: Color to treat as 'empty', defaults to the top left corner.
    :padding: Optional padding for image, default to 0.
    :keepRatio: Maintain the source images ratio, default True.
    
    '''
    
    if not chroma  == 'alpha':
        
        if chroma is None:
            chroma = img.pixel(0, 0)
        
        if img.hasAlphaChannel():
            chroma = 'alpha'
        
    left, top, right, bottom = identifyContent(img, chroma)
    
    src_width, src_height = img.width(), img.height()
    
    left = max(0, left - padding)
    right = min(src_width, right + padding)
    top  = max(0, top - padding)
    bottom = min(src_height, bottom + padding)
    
    new_width = (right - left)
    new_height = (bottom - top)
    
    if keepRatio:
        src_ratio = src_width / src_height
        new_ratio = new_width / new_height
        # This means the new image needs to be made taller
        if src_ratio < new_ratio:
            adjusted_height = round( (1 / src_ratio) * new_width)
            top, bottom = disperse(top, bottom, new_height, adjusted_height)
        
        # This means the new image needs to be made wider
        elif src_ratio > new_ratio:
            adjusted_width = round(src_ratio * new_height)
            left, right = disperse(left, right, new_width, adjusted_width)
    
    cropped = img.copy( left, top, right - left, bottom - top )
    
    return cropped


def identifyContent(img, chroma):
    ''' Taking a pixel at the give coord (or alpha), return the minimum rectangle containing content.
    
    Args:
        img: A Pixmap
        chroma: Either a pixel representing the chromakey or 'alpha' to use the alpha channel.
    '''
    #px = img.load()
    #chroma = px[x, y]

    if chroma == 'alpha':
        def column_is_empty(x):
            for y in range(img.height()):
                if QtGui.qAlpha(img.pixel(x, y)):
                    return False
            return True

        def row_is_empty(y):
            for x in range(img.width()):
                if QtGui.qAlpha(img.pixel(x, y)):
                    return False
            return True
    
    else:
        def column_is_empty(x):
            for y in range(img.height()):
                if img.pixel(x, y) != chroma:
                    return False
            return True

        def row_is_empty(y):
            for x in range(img.width()):
                if img.pixel(x, y) != chroma:
                    return False
            return True

    left = 0
    right = img.width()
    top = 0
    bottom = img.height()
    
    # For each side, test a strip moving in until a pixel with content is found
    for x in range(img.width()):
        if not column_is_empty(x):
            left = x
            break

    for x in range(img.width() - 1, 0, -1):
        if not column_is_empty(x):
            right = x
            break

    for y in range(img.height()):
        if not row_is_empty(y):
            top = y
            break

    for y in range(img.height() - 1, 0, -1):
        if not row_is_empty(y):
            bottom = y
            break
    
    return left, top, right, bottom


def disperse(lower, upper, newDim, adjustedDim):
    ''' Used to properly pad out an image to maintain the aspect ratio.
    '''
    delta = adjustedDim - newDim
    
    if delta % 2 == 0:
        lower -= delta / 2
        upper += delta / 2
    else:
        if lower - math.ceil(delta / 2) <= 0: # If favoring lower fits, do it
            lower -= int(math.ceil(delta / 2))
            upper += int(delta / 2)
        else:
            lower -= int(delta / 2)
            upper += int(math.ceil(delta / 2))
    
    return int(lower), int(upper)


def _globalTLBR(widget):
    ''' Helper to grab the global position of a widget. (Top Left Bottom Right)
    '''
    tl = widget.mapToGlobal(QPoint(0, 0))
    br = widget.mapToGlobal(QPoint(widget.width(), widget.height()))
    return tl.y(), tl.x(), br.y(), br.x()


def _drawHighlight(img, pen, x, y, width, height):

    paint = QtGui.QPainter()
    paint.begin(img)
    paint.setPen(pen)

    paint.drawRect(x, y, width, height )
    paint.end()


def grab(widget, highlight=None, pen='yellow'):
    try:
        img = widget.grab()
        offset = None
    except Exception:
        img = widget.parentWidget().grab()
        offset = widget.geometry()
        widget = widget.parentWidget()

    if highlight:
        if not isinstance(highlight, collections.abc.Iterable):
            highlight = [highlight]

        top, left, bottom, right = _globalTLBR(highlight[0])
        
        borderTL = widget.mapToGlobal(QPoint(0, 0))
        '''
        br = widget.mapToGlobal(QPoint(0, 0))
        tl = widget.mapToGlobal(QPoint(widget.width(), widget.height()))

        top, left, bottom, right = tl.y(), tl.x(), br.y(), br.x()
        origTop, origLeft = bottom, right
        '''

        for h in highlight[1:]:
            #tl = h.mapToGlobal(QPoint(0, 0))
            #br = h.mapToGlobal(QPoint(h.width(), h.height()))
            t, l, b, r = _globalTLBR(h)

            top = top if top <= t else t
            left = left if left <= l else l
            bottom = bottom if bottom >= b else b
            right = right if right >= r else r

        top -= borderTL.y()
        left -= borderTL.x()
        right -= borderTL.x()
        bottom -= borderTL.y()

        _drawHighlight(img, pen, left, top, right - left, bottom - top)
        '''
        paint = QtGui.QPainter()
        paint.begin(img)
        paint.setPen(pen)
        paint.drawRect(left, top, right - left, bottom - top)
        paint.end()
        '''

    if offset:
        img = img.copy( offset )

    return img


def grabTable(widget, highlightColumns=[], count=-1, pen='yellow'):
    img = widget.grab()

    header = widget.horizontalHeader()

    sizes = [header.sectionSize(i) for i in range(header.count())]
    highlightColumns.sort()
    left = sum( sizes[ :highlightColumns[0] ] )
    width = sum( sizes[highlightColumns[0]: highlightColumns[-1] + 1 ] )

    offset = header.mapToGlobal(QPoint(0, 0)) - widget.mapToGlobal(QPoint(0, 0))

    count = min(count, widget.rowCount()) if count >= 0 else widget.rowCount()
    rowHeights = sum( widget.rowHeight(i) for i in range(count) )

    # It looks like the horizontal header spans the width so offset.x() doesn't work
    x = 0
    vHeader = widget.verticalHeader()
    if vHeader:
        x += vHeader.geometry().width()

    _drawHighlight(img, pen, left + x, offset.y(), width, rowHeights + header.geometry().height())

    return img


def grabTree(widget, highlightColumns=[], count=-1, pen='yellow'):
    img = widget.grab()

    header = widget.header()

    sizes = [header.sectionSize(i) for i in range(header.count())]
    highlightColumns.sort()
    left = sum( sizes[ :highlightColumns[0] ] )
    width = sum( sizes[highlightColumns[0]: highlightColumns[-1] + 1 ] )

    offset = header.mapToGlobal(QPoint(0, 0)) - widget.mapToGlobal(QPoint(0, 0))

    it = QtWidgets.QTreeWidgetItemIterator(widget)
    heights = []

    count = count if count >= -1 else widget.rowCount()

    while it.value() and count:
        index = widget.indexFromItem(it.value())
        heights.append( widget.rowHeight(index) )

        it += 1
        count -= 1

    _drawHighlight(img, pen, left, offset.y(), width, header.geometry().height() + sum(heights))

    return img
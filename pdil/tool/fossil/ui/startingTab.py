
from .. import card as fossil_card  # Hack to not deal with the fact that "card" is a var used all over, thusly shadowing this import

from pymel.core import button, Callback, checkBox, intFieldGrp, menuItem, optionMenu, rowColumnLayout, text


class StartLayout( object ):
    def __init__( self, settingsObj ):
        rowColumnLayout(nc=2)

        # LegType UI
        text(l='Leg Type')
        self.legType = optionMenu( l='' )
        menuItem( l='Human' )
        menuItem( l='Dogleg' )
        settingsObj.settings.optionMenuSetup(self.legType, 'legType' )
    
        # Spine Orient UI
        text(l="Spine Orientation")
        self.spineOrient = optionMenu( l='')
        menuItem('Vertical')
        menuItem('Horizontal')
        settingsObj.settings.optionMenuSetup(self.spineOrient, 'spineOrient' )
    
        text(l='Number of Spine Joints')
        self.spineCount = intFieldGrp( nf=1, v1=settingsObj.settings.spineCount )
        text(l='Number of Fingers')
        self.fingerCount = intFieldGrp( nf=1, v1=settingsObj.settings.fingerCount )
        text(l="Thumb")
        self.thumb = checkBox(l='', v=settingsObj.settings.thumb)
    
        #setParent("..")
    
        text(l='')
        text(l='')
        text(l='')
        button(l="Start", w=300, c=Callback(self.start))
        
    def update( self ):
        pass
    
    def start( self ):
        fossil_card.bipedSetup(
            spineCount=self.spineCount.getValue()[0],
            numFingers=self.fingerCount.getValue()[0],
            legType=self.legType.getValue(),
            thumb=self.thumb.getValue(),
            spineOrient='vertical' if self.spineOrient.getValue() == 'Vertical' else 'horizontal',
        )
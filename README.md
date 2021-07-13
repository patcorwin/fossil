# fossil
Rigging and animation tools for Maya

Developed in 2022 and tested in Maya 2019, 2020.
Runs in both Python 3 and Python 2

## Requirements

Your imagination.

## Installation

### The Easy Way

I made a "fancy" installer, for this and other maya packages.

1. Save [this file](https://raw.githubusercontent.com/patcorwin/mayaHooks/master/mayaHooksInstaller.mel) anywhere as a ".mel", ex "install.mel", then simply drag it into a maya viewport to execute.
2. This will add mayaHooks and bring up a really ugly (for now) gui.  In the "Install from URL", paste in address of this repo, `https://github.com/patcorwin/fossil`
3. Reopen the gui, then you will see a shelf section under pdil to open fossil.
4. Drag it, and the mayaHooks shelf item, onto your own shelf.  Don't worry, the icons will regenerate if you want to put them on several shevles.

### Less Easy Way

Download, unzip and put the "pdil" folder in one of your Maya script folders.

To take full advantage of it, you will also want to add code to your userSetup.py found in userSetup_code.py.

## Philosophy
Making rigs manually is cumbersome and tedious because it takes many actions to follow through on a single decision.  When you have 3 joints: Shoulder, Elbow and Wrist, you probably are making an arm, and you probably want IK and FK controls for it.  But when creating rigs by hand, you name these joints, then name similar chains to control these joints, then name the controllers to match.

I want to make the act of laying out the joints to also be the same as creating the rig so you make one decision (I want an "arm") and do one action (place an arm card).  This convenience must be tempered with customizability because I want this to handle any bizarre creature.

Most importantly, every decision should be easily changed.  There is still lots of work to be done on this front, but the rig is able to rebuild many parts independently.


## Usage
Use the shelf item from mayaHooks or, in the script editor, in a Python tab, run:

```python
import pdil.tool.fossil.main
pdil.tool.fossil.main.RigTool()
```


### Simple Walkthrough

Here is a walkthrough just to get an idea of how to start making rigs.

* Open fossil as described in the Usage section.
* In an empty Maya scene, go to the 'Start' tab and add hit 'Start'.  This will make a basic biped.
  Each conceptual rig component is made as `Card`, which, ideally, makes it really easy to lay things out in broad strokes, as well as fine tune the individual joints.  This also makes clear the axis that the limb is intended to move on.
* After you're done fiddling around, go to the 'Editor' tab, hit 'Select All' then 'Build Bones'.  This makes all the bones, you can see how it made the other side for cards flagged to `Mirror` or `Inherited`
* Hit 'Select All' again, followed by 'Build Rig'.  This makes all the controls (defaulting into FK)
* Select on of the Elbow controls.  Use the bottom right section in the gui to change the shape from the dropdown and/or move the CVs around.
* Select the Shoulder card and hit 'Save Mods'.
* Select the Shoulder card and hit 'Delete Rig'.
* Select the Shoulder card and hit 'Build Rig'.
* Select the Shoulder card and hit 'Restore Mods'.  You're changes have now been reapplied!

### Ik/Fk
This is managed through an instanced shape on all the controls made by a card instead of putting it on one control, the might get hidden.  In the channel box will be a shape with a name ending in `FKIK_SWITCH`

Or got to "Artist Tools" tab and hit the button with the two encircling arrows.  Hover over any of the shelf buttons to see their name.

Drag them off the shelf onto yours.  Don't worry, they are regenerated on this shelf whenever fossil is opened.

### There are many more features, documentation coming soon.

Check the wiki
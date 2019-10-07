try:
    import mayaHooks.dagMenuProc
    mayaHooks.dagMenuProc.overrideDagMenuProc()
    
    import pdil.tool.animDagMenu
    mayaHooks.dagMenuProc.registerMenu(pdil.tool.animDagMenu.animationSwitchMenu)
    
except Exception:
    import traceback
    print( traceback.format_exc() )
    print( "See above error text, something went wrong in userSetup.py" )
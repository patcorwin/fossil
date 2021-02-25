try:
    import mayaHooks.override.dagMenuProc
    import pdil.tool.animDagMenu
    
    mayaHooks.override.dagMenuProc.callback_customDagMenu.register(pdil.tool.animDagMenu.animationSwitchMenu)
    
except Exception:
    import traceback
    print( traceback.format_exc() )
    print( "See above error text, something went wrong in userSetup.py" )
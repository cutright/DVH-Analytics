# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['dvha_app.py'],
             pathex=['./',
                     './venv/lib/python3.6/site-packages'],
             binaries=[('/System/Library/Frameworks/Tk.framework/Tk', 'tk'),
                       ('/System/Library/Frameworks/Tcl.framework/Tcl', 'tcl')],
             datas=[('./dvha/icons/', './dvha/icons/'),
                    ('./dvha/logo.png', './dvha/'),
                    ('./dvha/LICENSE', './dvha/'),
                    ('./dvha/db/create_tables.sql', './dvha/db/'),
                    ('./dvha/db/institutional.roi', './dvha/db/'),
                    ('./dvha/db/physician_BBM.roi', './dvha/db/')],
             hiddenimports=['sklearn.utils._cython_blas',
                            'sklearn.neighbors._typedefs',
                            'sklearn.neighbors._quad_tree',
                            'sklearn.tree._utils'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='dvha_app',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False)
app = BUNDLE(exe,
             name='DVH Analytics',
             icon='./dvha.icns',
             bundle_identifier=None,
             info_plist={'NSHighResolutionCapable': 'True'}
             )

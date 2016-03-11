"""
This script executes the main application for py2app.

Lots of paths need to be fixed.
"""
import os

if not os.path.exists('/usr/local/bin/cite'):
    os.system("""
cp /Applications/Cite.app/Contents/Resources/cite /usr/local/bin/cite
chmod +x /usr/local/bin/cite
              """)
path = os.path.join(os.environ['RESOURCEPATH'], 'lib',
                    'python2.7', 'lib-dynload')
frameworks = os.path.join(os.environ['RESOURCEPATH'], '..', 'Frameworks')

os.system("""
export PATH="$PATH:/usr/texbin:/Library/TeX/texbin:"
export PYTHONPATH="{}:$PYTHONPATH"
# export DYLD_PRINT_LIBRARIES=1
export DYLD_FRAMEWORK_PATH="{}:$DYLD_FRAMEWORK_PATH"
export DYLD_FALLBACK_LIBRARY_PATH=$DYLD_FALLBACK_LIBRARY_PATH/usr/lib:
python citeWindow.py
""".format(path, frameworks))

from distutils.core import setup
setup(name='patches',
      version='0.1',
      py_modules=['patchlib.apply', 'patchlib.build', 'patchlib.config',
                  'patchlib.data', 'patchlib.fetch', 'patchlib.gitcmd',
                  'patchlib.hooks', 'patchlib.mbox', 'patchlib.message',
                  'patchlib.notify', 'patchlib.query', 'patchlib.scan',
                  'patchlib.series', 'patchlib.util', 'patchlib.init'],
      scripts=['patches'])

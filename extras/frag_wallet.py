from sys import path,argv
path.append('..')

from armoryengine import *
import getpass

print ''
print '*'*80
print '* Executing wallet-fragmenting script.  Split your Armory wallet '
print '* into N pieces, requiring any M to recover the wallet.'
print '*'*80
print ''
try:
   from subprocess import Popen, PIPE
   proc = Popen('git rev-parse HEAD', shell=True, stdout=PIPE)
   commitHash = proc.stdout.read().strip()
   print 'Found hash of current commit:', commitHash
except:
   commitHash = None
   

if '--testnet' in argv:
   i = argv.index('--testnet')
   del argv[i]

if len(argv)<3:
   print ''
   print 'USAGE: %s <file.wallet> <m> <n> ' % argv[0]
   print ''
   print 'Will produce N files, of which any subset of M of them is '
   print 'sufficient to reproduce your wallet.'
   print ''
   exit(0)

wltfile,M,N  = argv[1:]
try:
   M = int(M)
   N = int(N)
except:
   print 'ERROR: Must specify integers for M and N'

if M>N:
   print 'ERROR: You must specify and M that is equal to or less than N'
   print '       You specified (M,N)=(%d,%d)' % (M,N)

if not 1<M<=8:
   print 'ERROR: You must select an M value between 2 and 8.'
   print '       Any value of N, greater than M, is valid.'

if not os.path.exists(wltfile):
   print 'Wallet file was not found: %s' % wltfile

# Read the wallet file
wlt  = PyBtcWallet().readWalletFile(wltfile)

netbyte = wlt.uniqueIDBin[-1]
if not netbyte==ADDRBYTE:
   print 'Wallet is for the wrong network!'
   print 'You are running on:  %s' % NETWORKS[ADDRBYTE]
   if NETWORKS.has_key(netbyte):
      print 'Wallet is for:       %s' % NETWORKS[netbyte]
   else:
      print 'Wallet is for:       Unknown Network(%s)' % binary_to_hex(netbyte)
   exit(0)

# If the wallet is encrypted, get the passphrase
if wlt.useEncryption:
   print 'Please enter your passphrase to unlock your wallet: '
   for ntries in range(3):
      passwd = SecureBinaryData(getpass.getpass('Wallet Passphrase: '))
      if wlt.verifyPassphrase(passwd):
         break;

      print 'Passphrase was incorrect!'
      if ntries==2:
         print 'Wallet could not be unlocked.  Aborting.'
         exit(0)

   print 'Correct Passphrase.  Unlocking wallet...'
   wlt.unlock(securePassphrase=passwd)
   passwd.destroy()


if wlt.watchingOnly:
   print 'ERROR: Root private key is not available in wallet!'
   exit(0)


# This function breaks strings/lines into pieces separated by s (usually space)
sp = lambda x,n,s: s.join([x[i*n:(i+1)*n] for i in range((len(x)-1)/n+1)])

root = wlt.addrMap['ROOT']
binPriv  = root.binPrivKey32_Plain.toBinStr()
binChain = root.chaincode.toBinStr()
print 'Please confirm that the following paper backup information is correct:'
print ''
print '   Root Key:  ', makeSixteenBytesEasy(binPriv[:16 ])
print '              ', makeSixteenBytesEasy(binPriv[ 16:])
print '   Chaincode: ', makeSixteenBytesEasy(binChain[:16 ])
print '              ', makeSixteenBytesEasy(binChain[ 16:])
print ''
conf = raw_input('Is this correct? [Y/n]: ')
if conf.lower().startswith('n'):
   print 'Aborting...'
   exit(0)



print 'About to create the fragments.  Any other info/identifiers you would '
print 'like to add to each of the fragment files?  Enter it on the next line: '
extraStr = raw_input('(Enter info or leave blank): ')

################################################################################
################################################################################
# Here's where the secret is split into pieces, checksummed, and converted to 
# easy-type-16 alphabet.  Then written out to file
dataOut = binPriv + binChain
pieces = SplitSecret(dataOut, M, N)

# We now have a matrix of x,y values, each value is 64-bytes
#   [ [ x0, y0]
#     [ x1, y1]
#        ...
#     [ xN, yN] ]

for f in range(N):
   wltID = wlt.uniqueIDB58
   dateStr = unixTimeToFormatStr(RightNow())
   fname = 'wallet_%s_frag%d_need_%d.txt' % (wltID, f+1, M)
   with open(fname, 'w') as fout:
      fout.write('Wallet ID:   %s\n' % wltID)
      fout.write('Create Date: %s\n' % dateStr)
      if commitHash:
         fout.write('Git Commit:  %s\n' % commitHash)
      fout.write(sp(extraStr, 80, '\n') + '\n\n')

      fout.write('This Fragment:     #%d\n' % (f+1))
      fout.write('Fragments Needed:   %d\n' % M)
      fout.write('Fragments Created:  %d (more fragments may have been created later)\n' % N)
      fout.write('\n\n')

      fout.write('The following is a single fragment of your wallet.  Execute \n')
      fout.write('the reconstruction script with any %d of these fragment files \n' % M)
      fout.write('in the execution directory to recover your original wallet.\n')
      fout.write('The files can be reconstructed by hand, and only need to contain\n')
      fout.write('the following 9 lines with the correct prefixes.\n')
      fout.write('\n')

      eightpcs = ''.join(pieces[f])
      eightpcs = [eightpcs[i*16:(i+1)*16] for i in range(8)]
      firstLine = int_to_hex(M) + int_to_hex(f+1) + binary_to_hex(wlt.uniqueIDBin)
      fout.write('ID: %s\n' % sp(firstLine,4,' '))
      print 'Fragment %d: %s' % (f+1, fname)
      print '    ID:', sp(firstLine, 4, ' ')
      for i in range(8):
         prefix = ('x' if i<4 else 'y') + str(i+1 if i<4 else i-3)
         toWrite = '%s: %s' % (prefix, makeSixteenBytesEasy(eightpcs[i]))
         fout.write(toWrite + '\n')
         print '   ', toWrite
      print ''


print ''
print 'NOTE: If you rerun this fragment script on the same wallet'
print '      with the same fragments-required value, M, then you will'
print '      get the same fragments.  Use this to replace fragments,'
print '      or using a higher N-value to produce more pieces (but you'
print '      MUST use the same M value!)'
print ''


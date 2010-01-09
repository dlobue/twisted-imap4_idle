from twisted.internet.ssl import ClientContextFactory
from twisted.mail  import imap4
from twisted.internet import protocol, defer

import termstyle

Command = imap4.Command

class IMAPFolderListProtocol(imap4.IMAP4Client):

    idle_folder = None
    _keepalive = None

    def lineReceived(self, line):
        if 'IDLE' in line or 'DONE' in line: print termstyle.red('DEBUG lineReceived-\n\t%s' % line)
        return imap4.IMAP4Client.lineReceived(self, line)
        #return super(IMAPFolderListProtocol, self).lineReceived(line)
        #return self.__super.lineReceived(line)

    def dispatchCommand(self, tag, rest):
        print termstyle.red('DEBUG dispatchCommand-\n\ttag: %s\n\trest: %s' % (tag, rest))
        return imap4.IMAP4Client.dispatchCommand(self, tag, rest)
        #return super(IMAPFolderListProtocol, self).dispatchCommand(tag, rest)
        #return self.__super.dispatchCommand(tag, rest)

    def serverGreeting(self, capabilities):
        login = self.login(self.factory.username, self.factory.password)
        login.addCallback(self.__loggedIn)
        login.chainDeferred(self.factory.deferred)

    def __loggedIn(self, results):
        self.state = 'AUTH'
        return self.IDLE('INBOX')

    def IDLE(self, folder):
        self.idle_folder = folder
        return self.select(folder).addCallback(self.__initIDLE)

    def __initIDLE(self, *args, **kwargs):
        print '__initIDLE'
        print 'args ', args
        print 'kwargs', kwargs

        cmd = 'IDLE'
        resp = ('IDLE',)
        d = self.sendCommand(Command(cmd, wantResponse=resp, continuation=self.__cbIDLE))
        d.addCallback(self.__cbterminateIDLE)
        return d

    def response_IDLE(self, tag, rest):
        print termstyle.blue('DEBUG response_IDLE')
        print termstyle.blue(tag)
        print termstyle.blue(rest)
        return tag, rest

    def IDLEDone(self):
        print termstyle.yellow('running IDLEDone')
        self.state = self._prev_state
        del self._prev_state
        cmd = 'DONE'
        cmd = Command(cmd)
        cmd.defer = defer.Deferred()
        self.sendLine(cmd.command)
        return cmd.defer

    def __cbterminateIDLE(self, *args, **kwargs):
        print termstyle.cyan('__cbterminateIDLE')
        print termstyle.cyan(args)
        print termstyle.cyan(kwargs)
        return self.logout()

    def __cbIDLE(self, rest):
        print termstyle.green('DEBUG- __cbIDLE\n\trest: %s' % rest)
        if self.state != 'IDLE' and 'accepted, awaiting DONE command' in rest or 'idling' in rest:
            print termstyle.green('idle start conditions found')
            #print self.waiting
            #print self._lastCmd
            #print self.tags
            self._prev_state = self.state
            self.state = 'IDLE'
            #self.keepAlive()
            reactor.callLater( 10, self.IDLEDone)
            return
            d = reactor.callLater( 30, self.IDLEDone)
            return d
        else:
            print termstyle.green('idle continuation')
            return rest

    def keepAlive(self):
        reactor.callLater(20, self.keepAlive)
        return self.noop()

    def connectionLost(self, reason):
        if not self.factory.deferred.called:
            # connection was lost unexpectedly!
            self.factory.deferred.errback(reason)

class IMAPFolderListFactory(protocol.ClientFactory):
    protocol = IMAPFolderListProtocol

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.deferred = defer.Deferred( )

    def stopFactory(self):
        print termstyle.magenta(termstyle.bold('stopping factory'))
        return

    def clientConnectionFailed(self, connection, reason):
        self.deferred.errback(reason)

if __name__ == "__main__":
    from twisted.internet import reactor
    import sys, getpass
    termstyle.enable()

    def printMailboxList(*args, **kwargs):
        print 'DEBUG- printMailboxList'
        print args
        print kwargs

        #list.sort( )
        #for box in list:
            #print box
            #reactor.stop( )

    def handleError(error):
        print >> sys.stderr, "Error:", error.getErrorMessage( )
        reactor.stop( )

    if not len(sys.argv) == 3:
        print "Usage: %s server login" % sys.argv[0]
        sys.exit(1)

    server = sys.argv[1]
    user = sys.argv[2]
    password = getpass.getpass("Password: ")
    factory = IMAPFolderListFactory(user, password)
    factory.deferred.addCallback(
        printMailboxList).addErrback(
        handleError)
    #reactor.connectTCP(server, 143, factory)
    icon = reactor.connectSSL(server, 993, factory, ClientContextFactory())
    reactor.run( )

from twisted.mail  import imap4
from twisted.internet import protocol, defer

class NotImplemented(Exception):
    """
    Method must be implemented by developer.
    """
    pass

class StateError(Exception):
    """
    The command used is not available in the connection's current state.
    """
    pass

class IMAPFolderListProtocol(imap4.IMAP4Client):

    _deferred_state = None
    idle_folder = None
    _keepalive = False

    def serverGreeting(self, capabilities):
        login = self.login(self.factory.username, self.factory.password)
        login.addCallback(self.__loggedIn)
        login.chainDeferred(self.factory.deferred)

    def __loggedIn(self, results):
        return self.IDLE('INBOX/MIEN/')

    def IDLE(self, folder):
        self.idle_folder = folder
        return self.select(folder).addCallback(self.__initIDLE)

    def __initIDLE(self, *args, **kwargs):
        cmd = 'IDLE'
        resp = ('IDLE',)
        d = self.sendCommand(imap4.Command(cmd, wantResponse=resp, continuation=self.__cbIDLE))
        d.addCallback(self.__cbterminateIDLE)
        return d

    def IDLENotify(self, tag, rest):
        """
        All IDLE responses from the server end up here.
        """
        raise NotImplemented

    def IDLEDone(self, *args, **kwargs):
        """
        What to do when IDLE is complete
        """
        raise NotImplemented

    def response_IDLE(self, tag, rest):
        return self.IDLENotify(tag, rest)

    def done(self):
        """
        Implements the DONE command, which will end the IDLE command.
        """
        if self.state != 'IDLE':
            raise StateError
        cmd = 'DONE'
        d = self.sendCommand(imap4.Command(cmd))
        return d

    def __cbterminateIDLE(self, *args, **kwargs):
        return self.IDLEDone()

    def __cbIDLE(self, rest):
        if 'accepted, awaiting DONE command' in rest:
            self._deferred_state = self.state
            self.state = 'IDLE'
            self._keepalive = True
            self.keepAlive()
            d = reactor.callLater( 300, self.done)
            return d
        else:
            return self.IDLENotify('+', rest) #FIXME

    def keepAlive(self):
        if self._keepalive:
            reactor.callLater(20, self.keepAlive)
            return self.noop()
        else: return

    def noop(self):
        print 'noop!'
        return imap4.IMAP4Client.noop(self)

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
        print 'stopping factory'
        self.protocol.IDLEDone()

    def clientConnectionFailed(self, connection, reason):
        self.deferred.errback(reason)

if __name__ == "__main__":
    from twisted.internet import reactor
    import sys, getpass

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
    reactor.connectTCP(server, 143, factory)
    reactor.run( )

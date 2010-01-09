from twisted.mail  import imap4
from twisted.internet import protocol, defer

Command = imap4.Command

class myCommand(imap4.Command):
    def format(self, tag=None):
        if tag is None:
            return self.command
        elif self.args is None:
            return ' '.join((tag, self.command))
        return ' '.join((tag, self.command, self.args))

class IMAPFolderListProtocol(imap4.IMAP4Client):

    idle_folder = None
    _keepalive = None

    def lineReceived(self, line):
        if 'IDLE' in line or 'DONE' in line: print 'DEBUG lineReceived-\n\t%s' % line
        return imap4.IMAP4Client.lineReceived(self, line)
        #return super(IMAPFolderListProtocol, self).lineReceived(line)
        #return self.__super.lineReceived(line)

    def dispatchCommand(self, tag, rest):
        print 'DEBUG dispatchCommand-\n\ttag: %s\n\trest: %s' % (tag, rest)
        return imap4.IMAP4Client.dispatchCommand(self, tag, rest)
        #return super(IMAPFolderListProtocol, self).dispatchCommand(tag, rest)
        #return self.__super.dispatchCommand(tag, rest)

    def serverGreeting(self, capabilities):
        login = self.login(self.factory.username, self.factory.password)
        login.addCallback(self.__loggedIn)
        login.chainDeferred(self.factory.deferred)

    def __loggedIn(self, results):
        self.state = 'AUTH'
        return self.IDLE('INBOX/MIEN/')
        #return self.list("", "*").addCallback(self.__gotMailboxList)

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
        print 'DEBUG response_IDLE'
        print tag
        print rest
        return tag, rest

    def sendCommand(self, cmd):
        cmd.defer = defer.Deferred()
        if self.waiting and cmd.command != 'DONE':
            self.queued.append(cmd)
            return cmd.defer
        elif self.waiting and cmd.command == 'DONE':
            #self.sendLine(cmd.format(self.waiting))
            self.sendLine(cmd.command)
            return cmd.defer
        t = self.makeTag()
        self.tags[t] = cmd
        self.sendLine(cmd.format(t))
        self.waiting = t
        self._lastCmd = cmd
        return cmd.defer

    def IDLEDone(self):
        print 'running IDLEDone'
        cmd = 'DONE'
        cmd = Command(cmd)
        cmd.defer = defer.Deferred()
        self.sendLine(cmd.command)
        return cmd.defer

    def __cbterminateIDLE(self, *args, **kwargs):
        print '__cbterminateIDLE'
        print args
        print kwargs
        return self.logout()

    def __cbIDLE(self, rest):
        print 'DEBUG- __cbIDLE\n\trest: %s' % rest
        if 'accepted, awaiting DONE command' in rest:
            #print self.waiting
            #print self._lastCmd
            #print self.tags
            self.state = 'IDLE'
            #self.keepAlive()
            reactor.callLater( 10, self.IDLEDone)
            return
            d = reactor.callLater( 30, self.IDLEDone)
            return d
        else:
            return rest

    def keepAlive(self):
        reactor.callLater(20, self.keepAlive)
        return self.noop()

    def noop(self):
        print 'noop!'
        return imap4.IMAP4Client.noop(self)

    def __gotMailboxList(self, list):
        return [boxInfo[2] for boxInfo in list]

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
        return
        return self.protocol.IDLEDone(protocol)

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

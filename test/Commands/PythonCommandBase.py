LOG=[]
class Stop(Exception): pass
class ImageProcPythonCommand:
    LIMIT=None
    def __init__(self, cam, gui=None): self.gui=gui
    def _rec(self,*a):
        LOG.append(a)
        if self.LIMIT and sum(1 for x in LOG if x[0]=='holdEnd')>=self.LIMIT: raise Stop()
    def press(self,b,duration=0.1,wait=0.1): self._rec('press',getattr(b,'name',b),duration,wait)
    def pressRep(self,b,repeat=1,duration=0.1,interval=0.1,wait=0.1): self._rec('pressRep',b.name,repeat,duration,interval,wait)
    def wait(self,t): self._rec('wait',float(t))
    def hold(self,b): self._rec('hold',b.name)
    def holdEnd(self,b): self._rec('holdEnd',b.name)
    def finish(self): self._rec('finish'); raise Stop()
    def start(self,ser,post): return 'started'

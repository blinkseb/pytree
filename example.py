from pytree import Tree, TreeModel, FloatCol, IntCol

import ROOT

class FourVector(TreeModel):
    p4  = ROOT.std.vector('ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiE4D<double>>>')
    pt  = ROOT.std.vector('float')
    eta = ROOT.std.vector('float')
    phi = ROOT.std.vector('float')
    e   = ROOT.std.vector('float')

class Lepton(FourVector):
    iso = FloatCol()

class Electron(Lepton.prefix('electron_')):
    pass

class Muon(Lepton.prefix('muon_')):
    pass

class Event(TreeModel):
    event = IntCol()
    lumi  = IntCol()
    run   = IntCol()
    rho   = FloatCol()
    npv   = IntCol()

class MainTreeModel(Electron, Muon, Event):
    pass

f = ROOT.TFile.Open('output.root', 'recreate')

tree = Tree('tree')

electron = Electron()
muon = Muon()

tree.set_buffer(electron, create_branches=True)
tree.set_buffer(muon, create_branches=True)

tree.muon_pt.push_back(5)

tree.fill(reset=True)

tree.write()

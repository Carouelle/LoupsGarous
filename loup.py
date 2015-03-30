#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import sys
import codecs
import traceback
import irclib
import ircbot
import random
import os
import string
import re
import xml.dom.minidom
from datetime import datetime
import ConfigParser

class Bot(ircbot.SingleServerIRCBot):
	
	##########
	# Fonction du bot
	
	#Connexion
	def __init__(self):
		config = ConfigParser.ConfigParser()
		if len(config.read("./prefs.ini")) == 0:
			print "Impossible de lire la configuration."
			sys.exit()

		self.pseudo = config.get("prefs", "pseudo")
		self.mdp = config.get("prefs", "mdp")
		self.chanJeu = config.get("prefs", "chanJeu")
		self.chanParadis = config.get("prefs", "chanParadis")
		self.chanLoups = config.get("prefs", "chanLoups")
		serveur = config.get("prefs", "serveur")
		port = config.getint("prefs", "port")
		
		print "Configuration :"
		print "\tPseudo :", self.pseudo
		print "\tMot de passe :", "oui" if len(self.mdp) > 0 else "non"
		print "\tServeur :", serveur + ":" + str(port)
		print "\tCanal de jeu :", self.chanJeu
		print "\tCanal des loups : ", self.chanLoups
		print "\tCanal du paradis : ", self.chanParadis
		print
		
		self.personnalite = None
		self.joueurs = []
		self.repliques = {}
		self.roles = {}
		self.declencheurs = {}
		self.repliquesDefault = {}
		self.rolesDefault = {}
		self.declencheursDefault = {}
		
		self.rolesSpeciaux = [self.roleChasseur, self.roleIdiot, self.roleSalvateur, self.roleAncien, self.roleCupidon, self.roleFille, self.roleSorciere, self.rolePolicier, self.roleCorbeau, self.roleEnfant]
		#self.rolesSpeciaux = [self.roleSorciere, self.roleEnfant]
		
		self.whisper = False
		self.whisperProba = [10, 30, 50, 80, 100]
		
		self.statut = "attente"
		self.demarre = False
		self.loups = []
		
		self.log = None
		
		self.nbPersonnalites = 10
		
		random.seed()
		
		self.debug("Test d'encodage : H� h� h�")
		
		ircbot.SingleServerIRCBot.__init__(self, [(serveur, port)], self.pseudo, "Maitre du jeu du loup garou")
		self.debug(u"Connexion...")
	
	#Donne une liste de personnalit�s au hasard parmi celles disponibles
	def listePersonnalites(self):
		fichiers = os.listdir('./personnalites/accepted')
		return random.sample(fichiers, self.nbPersonnalites)
		
	def extraireNomEtRepliques(self, fichier):
		document = xml.dom.minidom.parse(fichier)
		nb = 0
		
		for e in document.childNodes[0].childNodes :
			#R�cup�ration du nom
			if(e.localName == "nom"):
				nom = e.childNodes[0].nodeValue
				break
				
                for e in document.childNodes[0].childNodes :
			#R�cup�ration des r�pliques
			if(e.localName == "repliques"):
				for f in e.childNodes:
					if(f.localName == "dire"):
						for g in f.childNodes:
							if(g.localName == "cle"):
								nb += 1
								
                document.unlink()
                return nom, nb
	
	#Charge les r�pliques depuis le fichier XML
	def chargerRepliques(self, fichier):
		self.debug(u"Choix du fichier" + fichier)
		document = xml.dom.minidom.parse(fichier)
		repliques = {}
		roles = {}
		declencheurs = {}
		
		#R�cup�ration de la personnalit�
		for e in document.childNodes[0].childNodes :
			#R�cup�ration du nom
			if(e.localName == "nom"):
				self.personnalite = e.childNodes[0].nodeValue
			
			#R�cup�ration des r�les
			if(e.localName == "roles"):
				for f in e.childNodes:
					if(f.localName == "role"):
						roles[f.attributes["nom"].value] = f.childNodes[0].nodeValue
			
			#R�cup�ration des d�clencheurs
			elif(e.localName == "declencheurs"):
				for f in e.childNodes:
					if(f.localName == "declencheur"):
						declencheurs[f.attributes["nom"].value] = f.childNodes[0].nodeValue
						
			#R�cup�ration des r�pliques
			elif(e.localName == "repliques"):
				for f in e.childNodes:
					if(f.localName == "dire"):
						for g in f.childNodes:
							if(g.localName == "cle"):
								cle = g.childNodes[0].nodeValue
								if(cle in repliques):
									self.debug(u"NOES !")
									
								repliques[cle] = []
								
							elif(g.localName == "phrases"):
								for h in g.childNodes:
									if(h.localName == "phrase"):
										repliques[cle].append(h.childNodes[0].nodeValue)
		
		document.unlink()
		return [repliques, roles, declencheurs]
	
	#Envoie le message en utilisant la personnalit�
	def envoyer(self, destination, cle, variables = [], gras = True):
		replique = None
		
		if(cle in self.repliques):
			replique = self.repliques[cle]
			
		elif(cle in self.repliquesDefault):
			replique = self.repliquesDefault[cle]
		
		#Si la replique n'existe pas, on met directement la cl�
		if(replique != None):
			message = replique[random.randint(0, len(replique)-1)]
			noVariable = 1
			for variable in variables:
				message = message.replace("$" + str(noVariable), variable)
				noVariable = noVariable + 1
				
		else:
			message = cle
		
		#Le message n'est pas destin� au service : on rajoute le gras et on change quelques trucs
		if(gras):
			message = message[0].capitalize() + message[1:]
			message = message.replace(" de un ", " d'un ")
			#message = message.replace(" de le ", " du ")
			message = message.replace("1 votes", "1 vote")
			message = message.replace("1 personnes", "1 personne")
			message = message.replace(self.chanLoups + ".", self.chanLoups + " .")
			message = message.replace(self.chanLoups + ",", self.chanLoups + " ,")
			message = message.replace(self.chanLoups + "!", self.chanLoups + " !")
			message = message.replace(self.chanParadis + ".", self.chanParadis + " .")
			message = message.replace(self.chanParadis + ",", self.chanParadis + " ,")
			message = message.replace(self.chanParadis + "!", self.chanParadis + " !")
			
			if(self.demarre):
				
				if(destination == self.chanJeu or destination == self.chanLoups):
					mp = 'false'
				elif(destination.lower() in self.pseudos):
					mp = 'true'
				else:
					mp = 'none'
				
				if(mp != 'none'):
					try:
						self.addLog('chat', message, {'auteur' : self.pseudo, 'mp' : mp, 'destination' : destination}, 'logPartie')
					except:
						self.debug(u'Impossible d\'ajouter la r�plique au log')
			
			message = chr(2) + message
			
			
		self.debug(u"(" + destination + ") <" + self.pseudo + "> " + message)
		
		self.connection.privmsg(destination, message.encode("iso-8859-15", "ignore"))

	#Affiche un message en console
	def debug(self, message, gras = True):
		try:
			if(gras):
				print "\033[1;37m", message, "\033[0m"
			else:
				print message
		except Exception as e :
			try:
				#print message.encode('ascii', 'ignore')
				print unicode(message, errors="replace")
			except Exception as eb:
				print u"Erreur impression totale : ", str(eb)
	
	# �crit dans le log
	# self.addLog('action', self.victimeLoups, {'type' : 'mort', 'typeMort' : 'nuit', 'role' : self.identiteBrute(joueur)}, 'tour')
	def addLog(self, balise, texte = None, attributs = {}, fils = None):
		try:
			new = self.log.createElement(balise)
			
			for attribut in attributs:
				new.setAttribute(attribut, attributs[attribut])
			
			if(texte):
				textNode = self.log.createTextNode(texte)
				new.appendChild(textNode)
			
			if(fils):
				self.log.getElementsByTagName(fils)[-1].appendChild(new)
			else:
				self.log.childNodes[0].appendChild(new)
			
		except:
			self.debug(u"Erreur d'ecriture du log ! " + str(sys.exc_info()[1]))
	
	#Dis l'erreur sur le canal
	def erreur(self, erreur):
		self.envoyer(self.chanJeu, "ERREUR", [str(erreur)])
	
	#Traiter le message re�u
	def traiterMessage(self, serv, ev):
		message = ev.arguments()[0].strip().decode('iso-8859-15')
		regex = re.compile("\x1f|\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)
		message = regex.sub("", message)
		messageNormal = message
		message = message.lower()
		
		self.debug(u"(" + ev.target() + ") <" + irclib.nm_to_n(ev.source()) + "> " + messageNormal, False)
		
		if(self.demarre and ev.target().lower() == self.chanJeu.lower() or ev.target().lower() == self.chanLoups.lower()):
			try:
				self.addLog('chat', messageNormal, {'auteur' : irclib.nm_to_n(ev.source()), 'mp' : 'false', 'destination' : ev.target()}, 'logPartie')
			except:
				self.debug(u'Impossible d\'ajouter la r�plique au log')
		
		# Demande des r�les sur le paradis
		if(self.demarre and message == '!roles'  and ev.target().lower() == self.chanParadis.lower()):
			self.envoyerRolesAutresJoueurs(ev.source())
		#Jeu pas encore d�marr�
		elif(self.statut == "attente" and message == '!jouer'):
			self.demarrerJeu(serv)
		#Jeu d�marr�, �lection du pr�sentateur
		elif(self.statut == "votePresentateurs" and message.isdigit()):
			self.compterVotePresentateur(ev.source(), message)
		#Jeu d�marr�, attente des joueurs
		elif(self.statut == "appelJoueurs" and self.declencheurs['participer'] in message):
			self.ajouterJoueur(ev)
		# Vote pour chuchotement
		elif(self.statut == "voteChuchotement" and ("oui" in message or "non" in message)):
			self.voteChuchotement(ev.source(), message)
		#Jeu d�marr�, joueur n'ayant pas re�u son r�le
		elif('non' in self.declencheurs and self.declencheurs['non'] in message):
			self.envoyerRole(serv, ev.source())
		#Jeu d�marr�, joueur voulant connaitre les �quivalences
		elif('roles' in self.declencheurs and self.declencheurs['roles'] in message and ev.target().lower() == self.chanJeu.lower()):
			self.equivalencesRoles(serv, ev.source())
		#Message des loups sur qui ils veulent tuer
		elif(self.statut == "traiterCanalLoups" and ev.target().lower() == self.chanLoups.lower()):
			self.traiterMessageLoups(serv, ev.source(), message, messageNormal)
		#Message de demande de vote
		#elif(self.statut == "attenteVote" and self.declencheurs['voter'] in message):
		#	self.traiterDemandeVote(serv, ev.source())
		#Message de vote pour la lapidation
		elif(self.statut == "votesLapidation"):
			self.compterVoteLapidation(ev.source(), message)
		#Vote pour le maire
		elif(self.statut == "votesMaire"):
			self.compterVoteMaire(ev.source(), message)
		#Le maire d�partage ceux � �galit�
		elif(self.statut == "maireDepartage" and ev.source() == self.maire):
			self.lapidationMaire(message)
		# Spritisme en cours
		elif(self.statut == "spr" and ev.target().lower() == self.chanJeu.lower()):
			self.choix_spr(serv, ev.source(), message)
	
	#Traite le message priv� re�u
	def traiterMessagePrive(self, serv, ev):
		message = ev.arguments()[0].strip().decode('iso-8859-15')
		regex = re.compile("\x1f|\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)
		message = regex.sub("", message)
		messageNormal = message
		message = message.lower()
		
		self.debug(u"(MP) <" + irclib.nm_to_n(ev.source()) + "> " + messageNormal, False)
		
		if(self.demarre and ev.source() in self.joueurs):
			try:
				self.addLog('chat', messageNormal, {'auteur' : irclib.nm_to_n(ev.source()), 'mp' : 'true', 'destination' : self.pseudo}, 'logPartie')
			except:
				self.debug(u'Impossible d\'ajouter la r�plique au log')
		
		# Chuchotement
		if(self.demarre and self.whisper and ev.source() in self.joueurs and (('chuchoter' in self.declencheurs and self.declencheurs['chuchoter'] in message) or ('chuchoter' in self.declencheursDefault and self.declencheursDefault['chuchoter'] in message))):
			self.chuchoter(serv, ev.source(), message, messageNormal)
		#Appel de la voyante, et c'est la voyante
		elif(self.statut == "appelVoyante" and self.voyante == ev.source() and self.voyante != self.enPrison):
			self.messageVoyante(serv, message)
		#Appel du policier, et c'est le policier
		elif(self.statut == "appelPolicier" and self.policier == ev.source()):
			self.messagePolicier(serv, message)
		#Appel du salvateur, et c'est le salvateur
		elif(self.statut == "appelSalvateur" and self.salvateur == ev.source() and self.salvateur != self.enPrison):
			self.messageSalvateur(serv, message)
		#Appel du chasseur, et c'est le chasseur
		elif(self.statut == "demandeChasseur" and self.chasseur == ev.source()):
			self.messageChasseur(serv, ev.source(), message)
		#Appel de Cupidon, et c'est Cupidon
		elif(self.statut == "appelCupidon" and self.cupidon == ev.source()):
			self.messageCupidon(serv, message)
		#Appel de la sorci�re, et c'est la sorci�re
		elif((self.statut == "sorciereVie" or self.statut == "sorciereMort") and self.sorciere == ev.source() and self.sorciere != self.enPrison):
			self.messageSorciere(serv, message)
		#Appel du corbeau, et c'est le corbeau
		elif(self.statut == "appelCorbeau" and self.corbeau == ev.source() and self.corbeau != self.enPrison):
			self.messageCorbeau(serv, message)
		#Message pour le mur, faut que le gars soit encore vivant bien s�r
		elif(self.statut == "messageMurs" and ev.source() in self.joueurs):
			self.ajoutMurs(serv, ev.source(), messageNormal)
		#Message pour la candidature de Maire.
		elif(self.statut == "candidaturesMaire"  and ev.source() in self.joueurs and (self.idiot != ev.source() or (self.idiot == ev.source() and self.idiotVote))):
			self.candidatureMaire(ev.source(), messageNormal)
		#Message du maire mort pour son successeur
		elif(self.statut == "mortMaire" and ev.source() == self.maire):
			self.successeurMaire(serv, ev.source(), message)

	############
	# D�roulement du jeu

	#D�marre le jeu en envoyant les premi�res instructions
	def demarrerJeu(self, serv):
		
		self.log = xml.dom.minidom.parseString("<log></log>")
		self.addLog('date', datetime.today().strftime("%d/%m/%y %H:%M:%S"))
		self.addLog('logPartie')
		
		self.envoyer("chanserv", "clear " + self.chanParadis + " users", gras = False)
		self.envoyer("chanserv", "clear " + self.chanLoups + " users", gras = False)
		serv.execute_delayed(2, serv.join, [self.chanParadis])
		serv.execute_delayed(2, serv.join, [self.chanLoups])
		serv.execute_delayed(4, serv.mode, [self.chanLoups, "+m"])
		serv.execute_delayed(4, serv.mode, [self.chanLoups, "+i"])
		serv.execute_delayed(4, serv.mode, [self.chanLoups, "+s"])
		serv.execute_delayed(4, serv.mode, [self.chanParadis, "+i"])
		
		#Inviter Meuh
		#serv.execute_delayed(1, serv.invite, ["Meuh", self.chanParadis])
		#serv.execute_delayed(1, serv.invite, ["Meuh", self.chanLoups])
		
		self.envoyer(self.chanJeu, "Mesdames et messieurs, bienvenue dans cette nouvelle session de Loups-Garous !")
		personnalitesVote = self.listePersonnalites()
		self.debug(personnalitesVote)
		nom, nbRepliques = self.extraireNomEtRepliques('./personnalites/default/default.xml')
		nbRepliques = float(nbRepliques)
		stringPersonnaliteVote = u"0 : " + nom + " " 
		self.tableauPersonnalitesVote = {}
		self.tableauPersonnalitesVote[0] = 'default.xml'
		
		nb = 1
		for personnaliteVote in personnalitesVote:
		        nomAlt, nbRepliquesAlt = self.extraireNomEtRepliques('./personnalites/accepted/' + personnaliteVote)
		        pourcent = int(round((nbRepliquesAlt / nbRepliques) * 100)) 
			
			stringPersonnaliteVote += "%s : %s (%s%%). " % (str(nb), nomAlt, pourcent)
			self.tableauPersonnalitesVote[nb] = personnaliteVote
			nb += 1
			
		serv.execute_delayed(3, self.envoyer, [self.chanJeu, u"Nous avons de nombreux pr�sentateurs aujourd'hui. Votez pour votre pr�f�r�, en donnant simplement son chiffre. Chaque personalit�e est accompagn�e du pourcentage de r�pliques qui ont �t� adapt�es. Voici maintenant les pr�sentateurs propos�s :"])
		serv.execute_delayed(3, self.envoyer, [self.chanJeu, stringPersonnaliteVote])
		
		self.statut = "votePresentateurs"
		self.aVote = []
		self.votes = []
		
		#serv.execute_delayed(3, self.personnaliteeChoisie, [serv])
		serv.execute_delayed(30, self.personnaliteeChoisie, [serv])
	
	#On re�oit un vote pour le pr�sentateur
	def compterVotePresentateur(self, joueur, message):
		numeroVote = int(message)
		
		if(numeroVote >= 0 and numeroVote <= self.nbPersonnalites):
			self.debug(u"Vote pour " + str(numeroVote) + " de " + joueur)
			#Si le le joueur n'a pas d�j� vot�
			if(joueur not in self.aVote):
				self.aVote.append(joueur)
				self.votes.append(numeroVote)

	#La personnalit� a �t� �lue, on peut la charger et la lancer
	def personnaliteeChoisie(self, serv):
		
		#Si personne n'a vot�, on choisi par d�faut
		if(len(self.aVote) == 0):
			personnaliteChoisie = 0
		#On cherche le gagnant, si y'a une �galit� on choisit au pif parmi les ex-aequo
		else:
			maximum = 0
			personnalitesEgalite = []
			for personnalite in set(self.votes):
				if(self.votes.count(personnalite) > maximum):
					maximum = self.votes.count(personnalite)
					personnaliteChoisie = personnalite
					personnalitesEgalite = []
					personnalitesEgalite.append(personnalite)
					egalite = False
				elif(self.votes.count(personnalite) == maximum and maximum != 0):
					egalite = True
					personnalitesEgalite.append(personnalite)
			if(egalite):
				personnaliteChoisie = personnalitesEgalite[random.randint(0, len(personnalitesEgalite) - 1)]
						
		
		#Charge la personnalit� par d�faut
		chargement = self.chargerRepliques("./personnalites/default/default.xml")
		self.repliquesDefault = chargement[0]
		self.rolesDefault = chargement[1]
		self.declencheursDefault = chargement[2]
		
		#Charge la personnalit� choisie
		self.debug(u"Personnalite " + str(personnaliteChoisie) + " choisie")
		#chargement = self.chargerRepliques("./personnalites/default/default.xml")
		if(self.tableauPersonnalitesVote[personnaliteChoisie] == 'default.xml'):
			chargement = self.chargerRepliques("./personnalites/default/default.xml")
		else:
			chargement = self.chargerRepliques('./personnalites/accepted/' + self.tableauPersonnalitesVote[personnaliteChoisie])
		self.repliques = chargement[0]
		self.roles = chargement[1]
		self.declencheurs = chargement[2]
		
		#Si le d�clencheur n'existe pas dans la personnalit�, on la prend dans celle par d�faut
		for decl in self.declencheursDefault:
			if(decl not in self.declencheurs):
				self.declencheurs[decl] = self.declencheursDefault[decl]
		
		self.envoyer(self.chanJeu, u"Bien, les votes sont termin�s. Veuillez donc applaudir bien fort..." + self.personnalite + " !")
		self.addLog('personnalite', self.personnalite)
		serv.mode(self.chanJeu, "+N")
		serv.execute_delayed(6, self.envoyer, [self.chanJeu, "COMMENCER_JOUER"])
		serv.execute_delayed(10, self.envoyer, [self.chanJeu, "DIRE_PARTICIPER", [self.declencheurs['participer']]])
		
		#Liste des gens sur le canal
		self.pseudosPresents = []
		
		self.statut = "appelJoueurs"
		
		self.pseudos = {}
		self.joueurs = []
		self.loups = []
		self.villageois = []
		self.sv = []
		self.whisperProbaJoueurs = {}
		
		self.sprFonctions = [self.spr_memeCamp, self.spr_nombreRoles, self.spr_roleExiste, self.spr_sorcierePseudo, self.spr_loupsPseudo, self.spr_maireSV, self.spr_voyanteLoup, self.spr_estSV]
		
		#R�les sp�ciaux
		self.voyante = "non"
		self.voyanteObserveLoup = False
		
		self.chasseur = None
		self.secondeVictime = None
		
		self.salvateur = "non"
		self.salvateurDernier = None
		
		self.idiot = None
		self.idiotVote = True
		
		self.ancien = None
		self.ancienResiste = True
		
		self.cupidon = None
		self.amoureux1 = None
		self.amoureux2 = None
		
		self.sorciere = "non"
		self.sauvetageSorciere = None
		self.victimeSorciere = None
		self.potionVie = True
		self.potionMort = True
		
		self.fille = None
		self.loupsInconnus = {}
		
		self.policier = None
		self.enPrison = None
		
		self.corbeau = None
		self.victimeCorbeau = None
		
		self.enfant = None
		self.tuteur = None
		
		self.maire = None
		self.maireElu = False
		self.noJour = 0
		
		self.traitre = None
		
		self.victimeLoups = None
		
		#No du vote en cours
		self.noVote = 0
		
		serv.execute_delayed(60, self.verifierSuffisant, [serv, 0])
		#serv.execute_delayed(20, self.verifierSuffisant, [serv, 0])
	
	#Ajoute le joueur � la liste
	def ajouterJoueur(self, ev):
		
		#Si joueur pas d�j� pr�sent dans la liste
		if(ev.source() not in self.joueurs):
			self.debug(u"Participation de " + ev.source())
			
			#Ajout dans le dictionnaire des pseudos et la liste des joueurs
			self.pseudos[irclib.nm_to_n(ev.source()).lower()] = ev.source()
			self.whisperProbaJoueurs[ev.source()] = 0
			self.joueurs.append(ev.source())
			self.connection.mode(self.chanJeu, " +v " + irclib.nm_to_n(ev.source()))
	
	#V�rifie que le nombre de joueur est suffisant. Si oui, passe � l'�tape suivante. Sinon, attend encore
	def verifierSuffisant(self, serv, nbAppels):
		if(len(self.joueurs) < 4):
			if (nbAppels == 10):
				self.finir(serv, True);
			else:
				self.envoyer(self.chanJeu, "PAS_ASSEZ_DE_JOUEURS", [self.declencheurs['participer']])
				serv.execute_delayed(30, self.verifierSuffisant, [serv, nbAppels + 1])
		#Assez de joueurs
		else:
			if(len(self.joueurs) < 6):
				self.maxLoups = 1
			elif(len(self.joueurs) >= 6 and len(self.joueurs) < 11):
				self.maxLoups = 2
			elif(len(self.joueurs) >= 11 and len(self.joueurs) < 16):
				self.maxLoups = 3
			else:
				self.maxLoups = len(self.joueurs)/5
				
			self.minSv = len(self.joueurs)/3
				
			self.connection.mode(self.chanJeu, "+m")
			self.debutVotesChuchotement(serv)
	
	# Vote pour le chuchotement	
	def debutVotesChuchotement(self, serv):
		serv.who(self.chanJeu)
		self.demarre = True
		serv.execute_delayed(3, self.devoicerNonJoueurs, [serv])
		
		self.oui = 0
		self.non = 0
		self.listeVotesChuchotement = []
		self.statut = "voteChuchotement"
		
		self.envoyer(self.chanJeu, "VOTE_CHUCHOTEMENT")
		serv.execute_delayed(40, self.partieVaCommencer, [serv])
		
	# Re�oit un vote pour chuchotement
	def voteChuchotement(self, joueur, message):
		if(joueur not in self.listeVotesChuchotement):
			self.listeVotesChuchotement.append(joueur)
			if("oui" in message):
				self.oui += 1
			elif("non" in message):
				self.non += 1
				
			self.debug(u"Oui : " + str(self.oui) + " Non : " + str(self.non))
	
	#Donne quelques instructions avant le lancement de la partie	
	def partieVaCommencer(self, serv):
		if(self.statut != "voteChuchotement"):
			return
		
		if(self.oui >= self.non):
			self.whisper = True
		else:
			self.whisper = False
			
		self.debug(str(self.oui) + " " + str(self.non) + " " + str(self.whisper))
		
		self.envoyer(self.chanJeu, "PARTIE_VA_COMMENCER")
		serv.execute_delayed(3, self.envoyer, [self.chanJeu, "VA_ENVOYER_ROLES"])
		serv.execute_delayed(10, self.attributerRoles, [serv])
	
	#Devoice ceux qui ne jouent pas
	def devoicerNonJoueurs(self, serv):
		for pseudo in self.pseudosPresents :
			if(pseudo.lower() not in self.pseudos):
				serv.mode(self.chanJeu, " -v " + pseudo)
	
	#Attribue un r�le � chacun des joueurs et leur envoie un message pour leur donner
	def attributerRoles(self, serv):
		self.statut = "attribuerRoles"
		self.debug(u"Nombre de loups : ")
		self.debug(self.maxLoups)
		self.debug(u"Nombre minimal de SV : ")
		self.debug(self.minSv)
		
		random.shuffle(self.joueurs)
		random.shuffle(self.rolesSpeciaux)
		
		self.addLog('joueurs')
		
		attente = 0
		noRole = 0
		for joueur in self.joueurs:
			pseudo = irclib.nm_to_n(joueur)
			
			if(len(self.loups) < self.maxLoups):
				self.loups.append(joueur)
				self.loupsInconnus[joueur] = 'L' + str(len(self.loups))
				self.debug(self.loupsInconnus)
				self.addLog('joueur', pseudo, {'role' : 'loup'}, 'joueurs')
		
			elif(len(self.sv) < self.minSv):
				self.villageois.append(joueur)
				self.sv.append(joueur)
				self.addLog('joueur', pseudo, {'role' : 'villageois'}, 'joueurs')
			
			elif(self.voyante == "non"):
				self.villageois.append(joueur)
				self.roleVoyante(joueur)
			
			elif(noRole < len(self.rolesSpeciaux)):
				self.debug(u'Attribution r�le ' + str(noRole) + ' : ' + str(self.rolesSpeciaux[noRole]))
				self.villageois.append(joueur)
				self.rolesSpeciaux[noRole](joueur)
				noRole = noRole + 1
				
			else:
				self.villageois.append(joueur)
				self.sv.append(joueur)
				self.addLog('joueur', pseudo, {'role' : 'villageois'}, 'joueurs')
				
			identite = self.identite(joueur)
			serv.execute_delayed(attente, self.envoyer, [pseudo, "DONNER_ROLE", [identite]])
			attente = attente + 1
		
		random.shuffle(self.joueurs)
		serv.execute_delayed(attente + 5, self.verifierRolesRecus, [serv])
	
	#Fonctions d'attributions des r�les sp�ciaux
	def roleVoyante(self, joueur):
		self.voyante = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'voyante'}, 'joueurs')
		
	def roleChasseur(self, joueur):
		self.chasseur = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'chasseur'}, 'joueurs')
			
	def roleIdiot(self, joueur):
		self.idiot = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'idiot'}, 'joueurs')
				
	def roleSalvateur(self, joueur):
		self.salvateur = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'salvateur'}, 'joueurs')
				
	def roleAncien(self, joueur):
		self.ancien = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'ancien'}, 'joueurs')
				
	def roleCupidon(self, joueur):
		self.cupidon = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'cupidon'}, 'joueurs')
				
	def roleFille(self, joueur):
		self.fille = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'fille'}, 'joueurs')
				
	def roleSorciere(self, joueur):
		self.sorciere = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'sorciere'}, 'joueurs')
		
	def rolePolicier(self, joueur):
		self.policier = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'policier'}, 'joueurs')
		
	def roleCorbeau(self, joueur):
		self.corbeau = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'corbeau'}, 'joueurs')
		
	def roleEnfant(self, joueur):
		self.enfant = joueur
		self.addLog('joueur', irclib.nm_to_n(joueur), {'role' : 'enfant'}, 'joueurs')
	
	#Demande � tous les joueurs s'ils ont re�u leur r�le
	def verifierRolesRecus(self, serv):
		
		# On donne son tuteur � l'enfant loup
		if(self.enfant is not None):
			if(self.ancien is not None and self.ancien != "non"):
				self.tuteur = self.ancien
			elif(self.sorciere is not None and self.sorciere != "non"):
				self.tuteur = self.sorciere
			else:
				self.tuteur = self.voyante
			
			identite = self.identite(self.tuteur)
			self.debug("Tuteur : " + self.tuteur + ", Ident tuteur : " + identite)
			self.envoyer(irclib.nm_to_n(self.enfant), "DONNER_TUTEUR", [identite])
			self.addLog('tuteur', irclib.nm_to_n(self.tuteur))
		
		self.debug(u"Nombre final de SV : " + str(len(self.sv)))

		# 1 chance sur 2 d'avoir un traitre
		randomTraitre = random.randint(0, 10)

		self.debug(u"Random traitre : " + str(randomTraitre))
		if(len(self.sv) >= 4 and randomTraitre >= 5):
			self.traitre = random.sample(self.sv, 1)[0]
			self.debug(u"Traitre : " + str(self.traitre))
		else:
			self.traitre = None
			self.debug(u"Pas de traitre")
		
		self.statut = "verifierRolesRecus"
		self.envoyer(self.chanJeu, "ROLES_ENVOYES")
		
		serv.execute_delayed(3, self.envoyer, [self.chanJeu, "VERIFIER_ONGLET", [self.pseudo]])
		serv.execute_delayed(6, self.envoyer, [self.chanJeu, "DIRE_NON", [self.declencheurs['non']]])
		serv.execute_delayed(10, self.envoyer, [self.chanJeu, "DIRE_EQUIVALENCES_ROLES", [self.declencheurs['roles']]])
		
		attente = 20
		
		if(self.whisper):
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "COMMENT_CHUCHOTER", [self.declencheurs['chuchoter']]])
			attente += 10
		
		serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "QUELQUES_SECONDES"])
		
		#self.victimeLoups = None
		#self.salvateurDernier = None
		#self.sauvetageSorciere = None
		#self.victimeSorciere = None
		#serv.execute_delayed(11, self.passerJour, [serv])
		#serv.execute_delayed(1, self.votesLapidation, [serv])
		#serv.execute_delayed(1, self.appelLoups, [serv])
		#serv.execute_delayed(3, self.annoncerAttenteVote, [serv])
		#serv.execute_delayed(30, self.demarrerMurs, [serv])
		#serv.execute_delayed(5, self.appelSalvateur, [serv])
		#serv.execute_delayed(3, self.passerNuit, [serv])
		#self.messagesMurs = {}
		#serv.execute_delayed(3, self.lireMurs, [serv])
		
		# LE VRAI
		serv.execute_delayed(attente + 20, self.passerNuit, [serv])
	
	#Retourne le r�le d'un joueur � partir de son domaine
	def identite(self, joueur):
		if(joueur in self.loups):
			if("loup" in self.roles):
				return self.roles["loup"]
			else:
				return self.rolesDefault["loup"]
				
		elif(joueur == self.voyante):
			if("voyante" in self.roles):
				return self.roles["voyante"]
			else:
				return self.rolesDefault["voyante"]
				
		elif(joueur == self.chasseur):
			if("chasseur" in self.roles):
				return self.roles["chasseur"]
			else:
				return self.rolesDefault["chasseur"]
		
		elif(joueur == self.cupidon):
			if("cupidon" in self.roles):
				return self.roles["cupidon"]
			else:
				return self.rolesDefault["cupidon"]
			
		elif(joueur == self.salvateur):
			if("salvateur" in self.roles):
				return self.roles["salvateur"]
			else:
				return self.rolesDefault["salvateur"]
				
		elif(joueur == self.ancien):
			if("ancien" in self.roles):
				return self.roles["ancien"]
			else:
				return self.rolesDefault["ancien"]
				
		elif(joueur == self.idiot):
			if("idiot" in self.roles):
				return self.roles["idiot"]
			else:
				return self.rolesDefault["idiot"]
				
		elif(joueur == self.sorciere):
			if("sorciere" in self.roles):
				return self.roles["sorciere"]
			else:
				return self.rolesDefault["sorciere"]
				
		elif(joueur == self.fille):
			if("fille" in self.roles):
				return self.roles["fille"]
			else:
				return self.rolesDefault["fille"]
				
		elif(joueur == self.policier):
			if("policier" in self.roles):
				return self.roles["policier"]
			else:
				return self.rolesDefault["policier"]
				
		elif(joueur == self.corbeau):
			if("corbeau" in self.roles):
				return self.roles["corbeau"]
			else:
				return self.rolesDefault["corbeau"]
				
		elif(joueur == self.enfant):
			if("enfant" in self.roles):
				return self.roles["enfant"]
			else:
				return self.rolesDefault["enfant"]
				
		elif(joueur in self.villageois):
			if("sv" in self.roles):
				return self.roles["sv"]
			else:
				return self.rolesDefault["sv"]
				
		else:
			return None
	
	# Retourne le r�le brut d'un joueur � partir de son domaine	
	def identiteBrute(self, joueur):
		if(joueur in self.loups):
			return "loup"
				
		elif(joueur == self.voyante):
			return "voyante"
				
		elif(joueur == self.chasseur):
			return "chasseur"
		
		elif(joueur == self.cupidon):
			return "cupidon"
			
		elif(joueur == self.salvateur):
			return "salvateur"
				
		elif(joueur == self.ancien):
			return "ancien"
				
		elif(joueur == self.idiot):
			return "idiot"
				
		elif(joueur == self.sorciere):
			return "sorciere"
				
		elif(joueur == self.fille):
			return "fille"
				
		elif(joueur == self.policier):
			return "policier"
			
		elif(joueur == self.corbeau):
			return "corbeau"
			
		elif(joueur == self.enfant):
			return "enfant"
				
		elif(joueur in self.villageois):
			return "villageois"
				
		else:
			return None
	
	#Donne au joueur son r�le
	def envoyerRole(self, serv, source):
		pseudo = irclib.nm_to_n(source)
		identite = self.identite(source)
		if(identite != None):
			self.envoyer(pseudo, "RAPPEL_ROLE", [identite])
	
	#Donne l'�quivalent des roles
	def equivalencesRoles(self, serv, source):
		pseudo = irclib.nm_to_n(source)
		tout = ""
		for key in self.roles:
			tout += self.roles[key].capitalize() + ' = ' + self.rolesDefault[key].capitalize() + '. '
		self.envoyer(pseudo, tout);
	
	#Passe � l'�tape de nuit
	def passerNuit(self, serv):
		self.statut = "nuit"
		self.addLog('tour')
		
		self.envoyer(self.chanJeu, "NUIT_TOMBEE")
		
		#Si Cupidon est l� (premier tour), on l'appelle
		if (self.cupidon != None):
			self.statut = "appelCupidon"
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "APPEL_CUPIDON"])
			serv.execute_delayed(10, self.appelCupidon, [serv])
			serv.execute_delayed(60, self.appelPolicier, [serv])
		else:
			serv.execute_delayed(10, self.appelPolicier, [serv])
	
	#Appel de Cupidon
	def appelCupidon(self, serv):
		#Premier amoureux
		if(self.amoureux1 == None):
			self.envoyer(irclib.nm_to_n(self.cupidon), "DEMANDE_CUPIDON_1")
		
		#Second amoureux
		elif(self.amoureux2 == None):
			self.envoyer(irclib.nm_to_n(self.cupidon), "DEMANDE_CUPIDON_2", [irclib.nm_to_n(self.amoureux1)])
	
	#R�pond � Cupidon
	def messageCupidon(self, serv, message):
		if(message == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.cupidon), "CUPIDON_DEMANDE_PRESENTATEUR")
			
		elif(message not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.cupidon), "PSEUDO_INCONNU")
			
		else:
			if (self.amoureux1 == None):
				self.amoureux1 = self.pseudos[message]
				self.appelCupidon(serv)
				
			elif (self.amoureux2 == None):
				if (self.amoureux1 == self.pseudos[message]):
					self.envoyer(irclib.nm_to_n(self.cupidon), "CUPIDON_MEME_PSEUDO", [irclib.nm_to_n(self.amoureux1)])
					
				else:
					self.amoureux2 = self.pseudos[message]
					self.envoyer(irclib.nm_to_n(self.cupidon), "CUPIDON_CONFIRMATION")
					self.statut = "cupidonOk"
	
	#Appel du policier
	def appelPolicier(self, serv):
		if (self.cupidon != None):
			if (self.statut != "cupidonOk"):
				self.envoyer(self.chanJeu, "CUPIDON_LENT")
				self.amoureux1 = None
				self.amoureux2 = None
				
			else:
				self.envoyer(self.chanJeu, "CUPIDON_A_CHOISI")
				self.addLog('action', irclib.nm_to_n(self.amoureux1) + ';' + irclib.nm_to_n(self.amoureux2), {'type' : 'cupidon'}, 'tour')
				self.addLog('amoureux', irclib.nm_to_n(self.amoureux1))
				self.addLog('amoureux', irclib.nm_to_n(self.amoureux2))
				self.debug(irclib.nm_to_n(self.amoureux1))
				self.debug(irclib.nm_to_n(self.amoureux2))
				self.envoyer(irclib.nm_to_n(self.amoureux1), "MESSAGE_AMOUREUX", [irclib.nm_to_n(self.amoureux2)])
				self.envoyer(irclib.nm_to_n(self.amoureux2), "MESSAGE_AMOUREUX", [irclib.nm_to_n(self.amoureux1)])
				
			self.cupidon = None
		
		self.statut = "appelPolicier"
		
		#Pas/Plus de policier
		if(self.policier is None):
			self.statut = "policierOk"
			serv.execute_delayed(5, self.appelVoyante, [serv])
		else:
			self.envoyer(self.chanJeu, "APPEL_POLICIER")
			self.envoyer(irclib.nm_to_n(self.policier), "DEMANDE_POLICIER")
			serv.execute_delayed(30, self.appelVoyante, [serv])

	#R�pond au policier
	def messagePolicier(self, serv, message):
		
		if(message == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.policier), "POLICIER_DEMANDE_PRESENTATEUR")
			
		elif(message not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.policier), "PSEUDO_INCONNU")
			
		else:
			joueur = self.pseudos[message]
			if(joueur == self.enPrison):
				self.envoyer(irclib.nm_to_n(self.policier), "DEJA_ENFERME")
				
			else:
				self.enPrison = joueur
				self.addLog('action', irclib.nm_to_n(self.enPrison), {'type' : 'policier'}, 'tour')
				self.envoyer(irclib.nm_to_n(self.policier), "CONFIRMATION_POLICIER")
				self.envoyer(irclib.nm_to_n(joueur), "MESSAGE_PRISON") 
				self.statut = "policierOk"
				self.appelVoyante(serv)

	#Appel de la voyante
	def appelVoyante(self, serv):
		
		if(self.statut == "appelPolicier"):
			self.envoyer(self.chanJeu, "POLICIER_LENT")
			self.enPrison = None
			self.statut = "policierOk"
			
		if(self.statut != "policierOk"):
			self.debug(u"Check policier : " + self.statut)
			return
		
		self.statut = "appelVoyante"
		
		#Plus de voyante (ancien)
		if(self.voyante == "non"):
			self.statut = "voyanteOk"
			self.appelSalvateur(serv)
		#Voyante morte
		elif(self.voyante == None):
			self.statut = "voyanteOk"
			self.appelSalvateur(serv)
		else:
			self.envoyer(self.chanJeu, "APPEL_VOYANTE")
			if(self.voyante != self.enPrison):
				self.envoyer(irclib.nm_to_n(self.voyante), "DEMANDE_VOYANTE")
			serv.execute_delayed(30, self.appelSalvateur, [serv])
		
	#R�pond � la voyante
	def messageVoyante(self, serv, message):
		if(message == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.voyante), "VOYANTE_DEMANDE_PRESENTATEUR")
		elif(message not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.voyante), "PSEUDO_INCONNU")
		else:
			identite = self.identite(self.pseudos[message])
			identiteBrute = self.identiteBrute(self.pseudos[message])
			
			if(identiteBrute == "loup"):
				self.voyanteObserveLoup = True
			elif(identiteBrute == "enfant"):
				if("sv" in self.roles):
					identite = self.roles["sv"]
				else:
					identite = self.rolesDefault["sv"]
			
			self.envoyer(irclib.nm_to_n(self.voyante), "DONNER_IDENTITE_A_VOYANTE", [identite])
			self.addLog('action', irclib.nm_to_n(self.pseudos[message]), {'type' : 'voyante', 'role' : self.identiteBrute(self.pseudos[message])}, 'tour')
			self.statut = "voyanteOk"
			self.appelSalvateur(serv)
	
	#Appel du salvateur
	def appelSalvateur(self, serv):
		if(self.statut == "appelVoyante"):
			self.envoyer(self.chanJeu, "VOYANTE_LENTE")
			self.statut = "voyanteOk"
			
		if(self.statut != "voyanteOk"):
			self.debug(u"Check voyante : " + self.statut)
			return
		
		self.statut = "appelSalvateur"
		
		#Pas de salvateur
		if(self.salvateur == "non"):
			self.statut = "salvateurOk"
			self.appelLoups(serv)
		elif(self.salvateur == None):
			self.statut = "salvateurOk"
			self.appelLoups(serv)
		else:
			self.envoyer(self.chanJeu, "APPEL_SALVATEUR")
			if(self.salvateur != self.enPrison):
				self.envoyer(irclib.nm_to_n(self.salvateur), "DEMANDE_SALVATEUR")
			serv.execute_delayed(30, self.appelLoups, [serv])
			
	#R�pond au salvateur
	def messageSalvateur(self, serv, message):
		if(message == "moi"):
			message = irclib.nm_to_n(self.salvateur).lower()
		
		if(message == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.salvateur), "SALVATEUR_DEMANDE_PRESENTATEUR")
		elif(message not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.salvateur), "PSEUDO_INCONNU")
		else:
			joueur = self.pseudos[message]
			if(joueur == self.salvateurDernier):
				self.envoyer(irclib.nm_to_n(self.salvateur), "DEJA_PROTEGE")
			else:
				self.salvateurDernier = joueur
				self.envoyer(irclib.nm_to_n(self.salvateur), "CONFIRMATION_SALVATEUR") 
				self.statut = "salvateurOk"
				self.addLog('action', irclib.nm_to_n(joueur), {'type' : 'salvateur'}, 'tour')
				self.appelLoups(serv)
	
	#Appel les loups
	def appelLoups(self, serv):
		serv.join(self.chanLoups)
		
		if(self.statut == "appelSalvateur"):
			self.envoyer(self.chanJeu, "SALVATEUR_LENT")
			self.salvateurDernier = None
			self.statut = "salvateurOk"
			
		if(self.statut != "salvateurOk"):
			self.debug(u"Check salvateur : " + self.statut)
			return
			
		self.statut = "appelLoups"
		
		for joueur in self.joueurs:
			self.connection.mode(self.chanJeu, " -v " + irclib.nm_to_n(joueur))
			
		self.envoyer(self.chanJeu, "APPEL_LOUPS", [self.chanLoups])
		self.loupsSurCanal = 0
		self.victimeLoups = None
		self.aParlerLoup = False
		
		for loup in self.loups :
			if(loup != self.enPrison):
				serv.invite(irclib.nm_to_n(loup), self.chanLoups)
		
		if(self.fille != None and self.fille != self.enPrison):
			serv.execute_delayed(3, self.envoyer, [irclib.nm_to_n(self.fille), "APPEL_FILLE"])
		serv.execute_delayed(10, self.traiterCanalLoups, [serv]) 
		serv.execute_delayed(70, self.verifierLoups, [serv])
		
	#Si les loups n'ont pas encore choisi de victime, on zappe
	def verifierLoups(self, serv):
		self.debug(u"Check loups : " + str(self.statut))
		if(self.victimeLoups == None and self.statut == "traiterCanalLoups"):
			self.statut = "attaqueLoup"
			self.kickerLoups(serv)
	
	#Gueule s'il manque des loups
	def traiterCanalLoups(self, serv):
		self.statut = "traiterCanalLoups"
		if(self.loupsSurCanal < len(self.loups)):
			self.envoyer(self.chanLoups, "MANQUE_DES_LOUPS")
		
		#if(not self.aParlerLoup):
		#	self.envoyer(self.chanLoups, "INSTRUCTIONS_LOUPS", [self.declencheurs['tuerLoups']])
		#	self.debug(u"A parl� aux loups")
	
	#Traite les messages de mort des loups
	def traiterMessageLoups(self, serv, source, message, messageNormal):
		messageSplit = message.split(" ", 1)
		
		if(self.fille != None and self.fille != self.enPrison):
			if(source in self.loupsInconnus):
				messageFille = '<LG> ' + messageNormal
				self.envoyer(irclib.nm_to_n(self.fille), messageFille)
		
		if(messageSplit[0] == self.declencheurs['tuerLoups'] and len(messageSplit) > 1):
			pseudo = messageSplit[1]
			if(pseudo == self.pseudo.lower()):
				self.envoyer(self.chanLoups, "TUER_PRESENTATEUR")
			elif(pseudo not in self.pseudos):
				self.envoyer(self.chanLoups, "PSEUDO_INCONNU")
			elif(self.victimeLoups == None):
				self.victimeLoups = pseudo
				self.envoyer(self.chanLoups, "CONFIRMATION_LOUPS")
				self.statut = "attaqueLoup"
				serv.execute_delayed(5, self.kickerLoups, [serv])
	
	#Kick les loups une fois qu'ils ont choisi quelqu'un � tuer
	def kickerLoups(self, serv):
		for loup in self.loups:
			serv.kick(self.chanLoups, irclib.nm_to_n(loup))
			
		if(self.victimeLoups == None):
			self.envoyer(self.chanJeu, "LOUPS_LENTS")
			self.addLog('action', "", {'type' : 'loup'}, 'tour')
		else:
			self.envoyer(self.chanJeu, "LOUPS_ONT_CHOISI")
			self.addLog('action', self.victimeLoups, {'type' : 'loup'}, 'tour')
		
		for joueur in self.joueurs:
			self.connection.mode(self.chanJeu, " +v " + irclib.nm_to_n(joueur))
		
		self.sauvetageSorciere = None
		self.victimeSorciere = None
		
		#Sorci�re morte; il lui restait des potions
		if(self.sorciere == None and (self.potionVie or self.potionMort)):
			serv.execute_delayed(5, self.appelCorbeau, [serv])
			
		#Pas de sorci�re; ou sorci�re vivante mais plus de potion
		elif(self.sorciere == "non" or (not self.potionVie and not self.potionMort)):
			serv.execute_delayed(5, self.appelCorbeau, [serv])
		
		#Sorci�re vivante avec potion de vie uniquement, mais pas de victime loup
		elif(self.potionVie and not self.potionMort and self.victimeLoups == None):
			serv.execute_delayed(5, self.appelCorbeau, [serv])
		
		#Sorci�re vivante et avec des potions
		else:
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "APPEL_SORCIERE"])
			if(self.sorciere != self.enPrison):
				serv.execute_delayed(10, self.appelSorciere, [serv])
			else:
				self.debug(u"Sorciere en prison")
				self.statut = "sorciereVie"
			serv.execute_delayed(50, self.verifierSorciere, [serv])
	
	#Appelle la sorci�re
	def appelSorciere(self, serv):
		if(self.victimeLoups != None and self.potionVie and self.statut != "sorciereVie" and self.statut != "sorciereMort"):
			self.statut = "sorciereVie"
			self.envoyer(irclib.nm_to_n(self.sorciere), "SORCIERE_POTION_GUERISON", [self.victimeLoups.capitalize()])
			
		elif(self.potionMort and self.statut != "sorciereMort"):
			self.statut = "sorciereMort"
			self.envoyer(irclib.nm_to_n(self.sorciere), "SORCIERE_POTION_POISON")
			
		else:
			self.appelCorbeau(serv)
		
	#Message de la sorci�re
	def messageSorciere(self, serv, message):
		self.debug(self.statut)
		self.debug(u'Vie : ' + str(self.potionVie))
		self.debug(u'Mort : ' +str(self.potionMort))
		#�tape de la potion de gu�rison
		if(self.statut == "sorciereVie"):
			if("oui" in message):
				self.sauvetageSorciere = self.victimeLoups
				self.potionVie = False
				self.addLog('action', self.sauvetageSorciere, {'type' : 'sorciereVie'}, 'tour')
			else:
				self.sauvetageSorciere = None
			self.appelSorciere(serv)
		
		#�tape de la potion d'empoisonnement
		elif(self.statut == "sorciereMort"):
			if(message == "non"):
				self.appelSorciere(serv)
			else:
				if(message == self.pseudo.lower()):
					self.envoyer(irclib.nm_to_n(self.sorciere), "SORCIERE_TUER_PRESENTATEUR")	
				elif(message not in self.pseudos):
					self.envoyer(irclib.nm_to_n(self.sorciere), "PSEUDO_INCONNU")
				else:
					self.potionMort = False
					self.victimeSorciere = message
					self.addLog('action', self.victimeSorciere, {'type' : 'sorciereMort'}, 'tour')
					self.appelSorciere(serv)
					
	#Si la sorci�re est trop lente, tant pis
	def verifierSorciere(self, serv):
		self.debug(u"Check sorciere : " + str(self.statut))
		if(self.statut == "sorciereVie" or self.statut == "sorciereMort"):
			self.statut = "finSorciere"
			self.envoyer(self.chanJeu, "SORCIERE_LENTE")	
			serv.execute_delayed(5, self.appelCorbeau, [serv])
			
	#Appel du corbeau
	def appelCorbeau(self, serv):
		
		self.statut = "appelCorbeau"
		self.victimeCorbeau = None
		
		#Pas de corbeau
		if(self.corbeau == None):
			self.passerJour(serv)
		else:
			self.envoyer(self.chanJeu, "APPEL_CORBEAU")
			if(self.corbeau != self.enPrison):
				self.envoyer(irclib.nm_to_n(self.corbeau), "DEMANDE_CORBEAU")
			serv.execute_delayed(30, self.passerJour, [serv])
			
	#R�pond au corbeau
	def messageCorbeau(self, serv, message):
		if(message == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.corbeau), "CORBEAU_DEMANDE_PRESENTATEUR")
		elif(message == "non"):
			self.passerJour(serv)
		elif(message not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.corbeau), "PSEUDO_INCONNU")
		else:
			joueur = self.pseudos[message]
			self.victimeCorbeau = joueur
			self.addLog('action', irclib.nm_to_n(joueur), {'type' : 'corbeau'}, 'tour')
			self.passerJour(serv)
	
	#Passe au jour
	def passerJour(self, serv):
		if(self.statut != "appelCorbeau"):
			self.debug('Check passer jour : ' + str(self.statut))
			return
		
		self.statut = "jour"
		self.noJour = self.noJour + 1
		
		self.envoyer(self.chanJeu, "JOUR_SE_LEVE")
		
		if(self.victimeLoups != None and self.victimeLoups not in self.pseudos):
			self.victimeLoups = None
			self.debug(self.pseudos)
			self.debug(u'lolwut victime pas dans les pseudos ?')
		
		if(self.victimeLoups != None):
			self.debug(u"Victime : " + self.pseudos[self.victimeLoups])
		if(self.salvateurDernier != None):
			self.debug(u"Protege salvateur : " + self.salvateurDernier)
		if(self.sauvetageSorciere != None):
			self.debug(u"Protege sorciere : " + self.pseudos[self.sauvetageSorciere])
		if(self.ancien != None):
			self.debug(u"Ancien : " + self.ancien + ", resiste : " + str(self.ancienResiste))
		if(self.victimeSorciere != None):
			self.debug(u"Victime sorciere : " + self.pseudos[self.victimeSorciere])
			
		#Si pas de victime des loup ou victime prot�g�, aucune victime loup
		if(self.victimeLoups == None or self.pseudos[self.victimeLoups] == self.salvateurDernier or self.victimeLoups == self.sauvetageSorciere):
			self.debug(u"Pas de victime loup")
			self.victimeLoups = None
		
		#Si victime loup est ancien et qu'il n'avait jamais �t� attaqu�, aucune victime
		if(self.victimeLoups != None and self.pseudos[self.victimeLoups] == self.ancien and self.ancienResiste):
			self.debug(u"L'ancien resiste aux loups !")
			self.ancienResiste = False
			self.victimeLoups = None
		
		#Si pas de victime loup mais une victime sorci�re
		if(self.victimeLoups == None and self.victimeSorciere != None):
			self.debug(u"Une victime sorciere uniquement")
			self.victimeLoups = self.victimeSorciere
			self.victimeSorciere = None
		
		#Si les victimes sont les m�mes
		if(self.victimeLoups != None and self.victimeLoups == self.victimeSorciere):
			self.debug(u"Memes victimes loups et sorciere")
			self.victimeSorciere = None
		
		#Si pas de victime du tout
		if(self.victimeLoups == None and self.victimeSorciere == None):
			self.addLog('action', "", {'type' : 'mort'}, 'tour')
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "PERSONNE_N_A_ETE_TUE"])
			serv.execute_delayed(10, self.annoncerAttenteVote, [serv])
			
		#On tue la victime (soit loup, soit pas loup mais sorci�re)
		else:
			joueur = self.pseudos[self.victimeLoups]
			identite = self.identite(joueur)
			
			self.addLog('action', self.victimeLoups, {'type' : 'mort', 'typeMort' : 'nuit', 'role' : self.identiteBrute(joueur)}, 'tour')
			
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "MESSAGE_MORT_1"])
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "MESSAGE_MORT_2"])
			serv.execute_delayed(20, self.envoyer, [self.chanJeu, "MESSAGE_MORT_VICTIME", [self.victimeLoups.capitalize()]])
				
			if(joueur in self.loups):
				serv.execute_delayed(25, self.envoyer, [self.chanJeu, "VICTIME_LOUPS_ETAIT_LOUP", [self.victimeLoups.capitalize()]])
			else:
				serv.execute_delayed(25, self.envoyer, [self.chanJeu, "VICTIME_LOUPS_ETAIT_VILLAGEOIS", [self.victimeLoups.capitalize(), identite]])
					
			self.suivante = self.tuerVictimeSorciere
			self.tuer(20, joueur)
	
	#On tue la victime de la sorci�re, s'il y en a une
	def tuerVictimeSorciere(self, serv):
		if(self.victimeSorciere == None or self.victimeSorciere not in self.pseudos):
			self.debug(u"Pas de victime sorciere : " + str(self.victimeSorciere))
			self.annoncerAttenteVote(serv)
		else:
			joueur = self.pseudos[self.victimeSorciere]
			identite = self.identite(joueur)
			
			self.addLog('action', self.victimeSorciere, {'type' : 'mort', 'typeMort' : 'nuit', 'role' : self.identiteBrute(joueur)}, 'tour')
				
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "MESSAGE_AUTRE_MORT"])
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "MESSAGE_MORT_2"])
			serv.execute_delayed(20, self.envoyer, [self.chanJeu, "MESSAGE_MORT_VICTIME", [self.victimeSorciere.capitalize()]])
				
			if(joueur in self.loups):
				serv.execute_delayed(25, self.envoyer, [self.chanJeu, "VICTIME_LOUPS_ETAIT_LOUP", [self.victimeSorciere.capitalize()]])
			else:
				serv.execute_delayed(25, self.envoyer, [self.chanJeu, "VICTIME_LOUPS_ETAIT_VILLAGEOIS", [self.victimeSorciere.capitalize(), identite]])
					
			self.suivante = self.annoncerAttenteVote
			self.victimeSorciere = None
			self.tuer(20, joueur)
	
	#Le chasseur vient d'�tre tu�, on lui demande qui il tue en retour
	def chasseurTue(self):
		self.envoyer(self.chanJeu, "INSTRUCTIONS_CHASSEUR")
		self.connection.execute_delayed(3, self.envoyer, [irclib.nm_to_n(self.chasseur), "DEMANDE_CHASSEUR"])
		self.statut = "demandeChasseur"
		self.connection.execute_delayed(60, self.zapperChasseur, [self.chasseur])
		
	#Zappe le chasseur s'il n'a toujours choisi personne
	def zapperChasseur(self, ancienChasseur):
		if(self.statut == "demandeChasseur"):
			self.statut = "chasseurChoisi"
			self.envoyer(self.chanJeu, "CHASSEUR_LENT")
			#On le tue pour de vrai cette fois
			self.chasseur = None
			self.tuer(5, ancienChasseur, self.continuer)
			
	
	#Tue la personne d�sign�e par le chasseur	
	def messageChasseur(self, serv, source, message):
		pseudo = message
		if(pseudo == self.pseudo.lower()):
			self.envoyer(irclib.nm_to_n(self.chasseur), "TUER_PRESENTATEUR")
		elif(pseudo not in self.pseudos):
			self.envoyer(irclib.nm_to_n(self.chasseur), "PSEUDO_INCONNU")
		else:
			self.statut = "chasseurChoisi"
			self.envoyer(irclib.nm_to_n(self.chasseur), "CONFIRMATION_CHASSEUR")
			self.envoyer(self.chanJeu, "CHASSEUR_A_CHOISI")
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "TUER_VICTIME_CHASSEUR", [pseudo.capitalize()]])
			
			joueur = self.pseudos[pseudo]
			identite = self.identite(joueur)
			
			self.addLog('action', pseudo, {'type' : 'mort', 'typeMort' : 'chasseur', 'role' : self.identiteBrute(joueur)}, 'tour')
			
			if(joueur in self.loups):
				serv.execute_delayed(10, self.envoyer, [self.chanJeu, "VICTIME_CHASSEUR_ETAIT_LOUP", [pseudo.capitalize()]])
			else:
				serv.execute_delayed(10, self.envoyer, [self.chanJeu, "VICTIME_CHASSEUR_ETAIT_VILLAGEOIS", [pseudo.capitalize()  ,identite]])
			
			#On enl�ve le chasseur maintenant
			self.chasseur = None
			self.secondeVictime = joueur
			self.tuer(15, source, False)
			
			"""
			#On l'invite sur les canaux
			self.connection.invite(irclib.nm_to_n(self.chasseur), self.chanParadis)
			self.connection.invite(irclib.nm_to_n(self.chasseur), self.chanLoups)
			
			#Lui envoyer un message pour lui dire
			self.connection.execute_delayed(5, self.envoyer, [irclib.nm_to_n(self.chasseur), "MESSAGE_AU_MORT", [self.chanParadis, self.chanLoups]])
			
			self.tuer(15, joueur, False)
			
			if (self.chasseur == self.amoureux1):
				self.chasseur = None
				self.connection.execute_delayed(20, self.tueAmoureux, [self.amoureux2])
				return
				
			if (self.chasseur == self.amoureux2):
				self.chasseur = None
				self.connection.execute_delayed(20, self.tueAmoureux, [self.amoureux1])
				return
			
			#On enl�ve le chasseur maintenant
			self.chasseur = None
			
			#Si personne n'a gagn�, on ex�cute la fonction suivante
			if(self.verifierVictoire(25) == 0):
				serv.execute_delayed(25, self.suivante, [serv])
			"""
				
	#Tue les absents puis annonce l'attente des votes
	def annoncerAttenteVote(self, serv):
		self.pseudosPresents = []
		serv.who(self.chanJeu)
		self.suivante = self.votesLapidation
		self.debug(u"Who effectu�")
		serv.execute_delayed(6, self.tuerAbsents, [serv])
	
	#Donne les instructions concernant l'�lection du maire
	def demarrerElection(self, serv):
		self.statut = "candidaturesMaire"
		self.envoyer(self.chanJeu, "INSTRUCTIONS_MAIRE")
		self.messagesCandidats = {}
		serv.execute_delayed(60, self.verifierCandidats, [serv])
		
	#Message pour �tre candidat
	def candidatureMaire(self, source, message):
		pseudo = irclib.nm_to_n(source)
		
		if (pseudo not in self.messagesCandidats):
			self.messagesCandidats[pseudo] = []
		
		#Si le message est trop long, on le coupe
		if(len(message) > 250):
			message = message[0:250] + '...'
		
		#Si la personne a d�j� envoy� 5 messages, on l'ignore
		if(len(self.messagesCandidats[pseudo]) < 5):
			self.messagesCandidats[pseudo].append(message)
			
		self.debug(self.messagesCandidats)
	
	#V�rifie qu'il y a des candidats, lit leurs messages puis lance les votes
	def verifierCandidats(self, serv):
		#Aucun candidat, on laisse tomber
		if(len(self.messagesCandidats) == 0):
			self.envoyer(self.chanJeu, "AUCUN_CANDIDAT")
			serv.execute_delayed(10, self.votesLapidation, [serv])
			return
		
		self.envoyer(self.chanJeu, "LECTURE_CANDIDATURES")
		
		attente = 5
		for candidat in self.messagesCandidats:
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, candidat + ' :'])
			self.debug(self.messagesCandidats[candidat])
			for message in self.messagesCandidats[candidat]:
				attente = attente + 3
				self.debug(u'Attente ' + str(attente))
				serv.execute_delayed(attente, self.envoyer, [self.chanJeu, '"' + message + '"'])
			attente = attente + 5
				
		serv.execute_delayed(attente + 5, self.envoyer, [self.chanJeu, "DEBUT_VOTE_MAIRE", [self.declencheurs['voterMaire']]])
		
		serv.execute_delayed(attente + 60, self.passerVoteMaire, [serv])
		self.candidats = map(str.lower, self.messagesCandidats.keys())
		self.votesMaire = []
		self.aVoteMaire = []
		self.statut = "votesMaire"
		
		self.addLog('votes', "", {'type' : 'maire'}, 'tour')
	
	def compterVoteMaire(self, joueur, message):
		messageSplit = message.split(" ", 1)
		if(messageSplit[0] == self.declencheurs['voterMaire'] and len(messageSplit) > 1):
			pseudo = messageSplit[1]
			self.debug(u"Vote pour " + messageSplit[1] + " de " + joueur)
			
			#Si le pseudo s'est pr�sent� et que le joueur n'a pas d�j� vot�
			if(pseudo in self.candidats and joueur not in self.aVoteMaire):
				self.aVoteMaire.append(joueur)
				self.votesMaire.append(pseudo)
				self.debug(self.votesMaire)
				self.addLog('vote', joueur, {'pour' : pseudo}, 'votes')
				
				#Si tout le monde a vot�, on peut continuer directement
				if(len(self.aVoteMaire) == len(self.joueurs)):
					self.verifierVotesMaire(self.connection)
	
	#Passe aux r�sultats des �l�ctions si les votes sont encore en cours
	def passerVoteMaire(self, serv):
		if(self.statut == "votesMaire"):
			self.verifierVotesMaire(serv)
	
	#V�rifie qu'il y a des votes, puis donne son statut de maire � la personne choisie
	def verifierVotesMaire(self, serv):
		self.statut = "votesMaireFini"
		
		#Personne n'a vot� ?
		if(len(self.aVoteMaire) == 0):
			self.addLog('resultat', "", {'type' : 'aucun'}, 'votes')
			self.envoyer(self.chanJeu, "AUCUN_VOTE_MAIRE")
			serv.execute_delayed(10, self.votesLapidation, [serv])
			return
			
		maximum = 0
		joueurDesigne = None
		joueursEgalite = []
		egalite = False
		
		self.envoyer(self.chanJeu, "VOTE_MAIRE_TERMINE")
		
		for joueur in set(self.votesMaire):
			if(self.votesMaire.count(joueur) > maximum):
				maximum = self.votesMaire.count(joueur)
				joueurDesigne = joueur
				joueursEgalite = []
				joueursEgalite.append(joueur)
				egalite = False
			elif(self.votesMaire.count(joueur) == maximum and maximum != 0):
				egalite = True
				joueursEgalite.append(joueur)
				
		if(not egalite):
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "NOUVEAU_MAIRE", [joueurDesigne.capitalize(), str(self.votesMaire.count(joueurDesigne))]])
			self.addLog('resultat', joueurDesigne.capitalize(), {'type' : 'majorite'}, 'votes')
		else:
			joueursEgaliteString = ', '.join(joueursEgalite)
			joueursEgaliteString = string.capwords(joueursEgaliteString)
			li = joueursEgaliteString.rsplit(',', 1)
			joueursEgaliteString = ' et'.join(li)
			joueurDesigne = joueursEgalite[random.randint(0, len(joueursEgalite) - 1)]
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "NOUVEAU_MAIRE_EGALITE", [joueursEgaliteString, str(self.votesMaire.count(joueursEgalite[0])), joueurDesigne.capitalize()]])
			self.addLog('resultat', joueurDesigne.capitalize(), {'type' : 'egalite'}, 'votes')
		
		self.maire = self.pseudos[joueurDesigne]
		serv.execute_delayed(15, self.votesLapidation, [serv])
	
	"""
	def annoncerAttenteVote_2(self, serv):
		
		#Si c'est le jour 2, on proc�de d'abord � l'�lection du maire
		self.debug(u'D�but du jour ' + str(self.noJour))
		
		if(self.noJour == 2 and not self.maireElu):
			self.maireElu = True
			self.demarrerElection(serv)
			return
		
		if(len(self.joueurs) > 5):
			if(len(self.joueurs)/2 > 5):
				self.minimumConfirmation = (len(self.joueurs)/2)
			else:
				self.minimumConfirmation = 5
		else:
			self.minimumConfirmation = len(self.joueurs) - 1
		
		#Si l'idiot ne peut plus voter, on enl�ve son vote
		if(self.idiot != None and not self.idiotVote):
			self.minimumConfirmation = self.minimumConfirmation - 1
		
		serv.execute_delayed(5, self.envoyer, [self.chanJeu, "MESSAGE_LAPIDATION_1"])
		serv.execute_delayed(10, self.envoyer, [self.chanJeu, "MESSAGE_LAPIDATION_2", [str(self.minimumConfirmation), self.declencheurs['voter']]])
		self.joueursDemandant = []
		serv.execute_delayed(10, self.passerAttenteVote, [serv])
		
	#Passe en mode d'attente des votes
	def passerAttenteVote(self, serv):
		self.statut = "attenteVote"
		self.noVote = self.noVote + 1
		serv.execute_delayed(240, self.debatsTropLongs, [serv, self.noVote])
		
	#Passe aux votes au bout d'un moment si ce n'est pas d�j� le cas
	def debatsTropLongs(self, serv, noVote):
		if(self.statut == "attenteVote" and noVote == self.noVote):
			self.envoyer(self.chanJeu, "DEBAT_LENTS")
			self.votesLapidation(serv)
	
	#Traiter demande vote
	def traiterDemandeVote(self, serv, joueur):
		self.debug(joueur + " veut voter.")
		#Si le joueur n'a pas d�j� demand�, que ce n'est pas l'idiot, ou que c'est l'idiot et qu'il vote
		if(joueur not in self.joueursDemandant and (self.idiot != joueur or (self.idiot == joueur and self.idiotVote))):
			self.joueursDemandant.append(joueur)
		
		self.debug(len(self.joueursDemandant))
		if(len(self.joueursDemandant) == self.minimumConfirmation):
			self.votesLapidation(serv)
	"""
	
	#Passe aux votes
	def votesLapidation(self, serv):
		#Si c'est le jour 2, on proc�de d'abord � l'�lection du maire
		self.debug(u'D�but du jour ' + str(self.noJour))
		
		if(self.noJour == 2 and not self.maireElu):
			self.maireElu = True
			self.demarrerElection(serv)
			return
		
		self.statut = "votesLapidation"
		self.votes = {}
		#self.votes = []
		#self.aVote = []
		self.JoueursEgalite = []
		self.noVote = self.noVote + 1
		
		self.egalite = False
		self.doubleEgalite = False
		
		self.votesPourPresentateur = 0
		
		self.addLog('votes', "", {'type' : 'lapidation'}, 'tour')
		
		self.envoyer(self.chanJeu, "MESSAGE_LAPIDATION_1")
		serv.execute_delayed(5, self.envoyer, [self.chanJeu, "COMMENT_LAPIDER", [self.declencheurs['tuerLapidation']]])
		
		if(self.victimeCorbeau is not None):
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "VOTES_CORBEAU", [irclib.nm_to_n(self.victimeCorbeau)]])
		
		#serv.execute_delayed(30, self.avertissementLapidation, [serv, self.noVote])
		#serv.execute_delayed(60, self.faireLapidation, [serv, 0, self.noVote])
		
		serv.execute_delayed(240, self.avertissementLapidation, [serv, self.noVote])
		serv.execute_delayed(300, self.faireLapidation, [serv, 0, self.noVote])
	
	#Ajoute le vote
	def compterVoteLapidation(self, joueur, message):
		messageSplit = message.split(" ", 1)
		if(messageSplit[0] == self.declencheurs['tuerLapidation'] and len(messageSplit) > 1):
			pseudo = messageSplit[1]
			self.debug(u"Vote pour " + messageSplit[1] + " de " + joueur)
			
			if(pseudo == self.pseudo.lower()):
				self.votesPourPresentateur = self.votesPourPresentateur + 1 
			#Si le pseudo existe
			elif(pseudo in self.pseudos):
				#Et que c'est pas l'idiot, ou que c'est l'idiot et qu'il a le droit de voter
				if((joueur != self.idiot)  or (joueur == self.idiot and self.idiotVote)):
					#Si �galit�, on v�rifie que le joueur concern� est dans les �galitaires
					if(not self.egalite or (self.egalite and pseudo in self.joueursEgalite)):
						
						# S'il a d�j� vot�, on annule son vote
						if(joueur in self.votes):
							del self.votes[joueur]
							
						#self.aVote.append(joueur)
						self.votes[joueur] = pseudo
						#self.addLog('votant', joueur, {'vote' : pseudo}, 'votes')
						
						#Si c'est le maire et qu'il y a encore dix joueurs, il a deux votes
						if(joueur == self.maire and len(self.joueurs) >= 10):
							if(joueur + "_maire" in self.votes):
								del self.votes[joueur + "_maire"]
								
							self.votes[joueur + "_maire"] = pseudo
							
						self.debug(self.votes)
						
						if(self.maire is not None and len(self.joueurs) >= 10):
							total = len(self.joueurs) + 1
						else:
							total = len(self.joueurs)
							
						if(not self.idiotVote):
							self.debug(u"Idiot ne vote pas")
							total -= 1
							
						majorite = round(total / 2) + 1
						actuel = self.votes.values().count(pseudo)
						
						self.debug(u"Total : " + str(total) + u", Vot� : " + str(len(self.votes)) +  u", Majorit� : " + str(majorite) + u", Actuel : " + str(actuel)) 
						
						# Si tout le monde a vot� ou majorit� absolue
						if(len(self.votes) == total or actuel >= majorite):
							self.lapidation(self.connection, 0)
	
	# Avertit qu'il ne reste qu'une minute
	def avertissementLapidation(self, serv, noVote):
		self.debug(u"Avertissement : " + self.statut + " " + str(noVote) + " " + str(self.noVote))
		
		if(self.statut != "votesLapidation" or noVote != self.noVote):
			return
		
		self.envoyer(self.chanJeu, "LAPIDATION_UNE_MINUTE")
	
	def faireLapidation(self, serv, nbAppels, noVote):
		self.debug(u"FaireLapidation : " + self.statut + " " + str(noVote) + " " + str(self.noVote))
		
		if(self.statut != "votesLapidation" or noVote != self.noVote):
			return
		
		self.lapidation(serv, nbAppels)

	#V�rifie les votes et lapide le...gagnant
	def lapidation(self, serv, nbAppels):
		
		self.debug("Victime corbeau : " + str(self.victimeCorbeau))
		if(self.victimeCorbeau is not None):
			self.votes["corbeau1"] = irclib.nm_to_n(self.victimeCorbeau).lower()
			self.votes["corbeau2"] = irclib.nm_to_n(self.victimeCorbeau).lower()
			self.debug(self.votes)
			self.victimeCorbeau = None
		
		#Personne n'a vot� ?
		if(len(self.votes) == 0):
			if (nbAppels == 1):
				self.egalite = True
				self.doubleEgalite = True
			else:
				self.envoyer(self.chanJeu, "PAS_ASSEZ_VOTES")
				serv.execute_delayed(20, self.faireLapidation, [serv, nbAppels + 1, self.noVote])
				return 0
		
		self.statut = "lapidationTerminee"
		self.envoyer(self.chanJeu, "VOTES_TERMINES_1")
		serv.execute_delayed(5, self.envoyer, [self.chanJeu, "VOTES_TERMINES_2"])
		
		attente = 10
		maximum = 0
		joueurDesigne = None
		self.joueursEgalite = []
		
		if(self.egalite):
			self.doubleEgalite = True
		
		if(len(self.votes) > 0):
			self.egalite = False
		
		#On regarde qui a le plus de vote
		for joueur in set(self.votes.values()):
			nb = self.votes.values().count(joueur)
			
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "NOMBRE_VOTES_POUR_JOUEUR", [joueur.capitalize(),  str(nb)]])
			attente = attente + 5
			if(nb > maximum):
				maximum = nb
				joueurDesigne = joueur
				self.joueursEgalite = []
				self.joueursEgalite.append(joueur)
				self.egalite = False
			elif(nb == maximum and maximum != 0):
				self.egalite = True
				self.joueursEgalite.append(joueur)
				
		# Ecriture des votes dans le log
		for votant in self.votes:
			self.addLog('votant', votant, {'vote' : self.votes[votant]}, 'votes')
		
		if(self.votesPourPresentateur > 0):
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "VOTE_POUR_PRESENTATEUR", [self.pseudo,  str(self.votesPourPresentateur)]])
			attente = attente + 5
		
		if(self.egalite and self.doubleEgalite):
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "DEUXIEME_EGALITE"])
			self.addLog('resultat', "", {'type' : 'egalite'}, 'votes')
			
			#Personne n'a gagn� ?
			if(self.verifierVictoire(attente) == 0):
				serv.execute_delayed(attente+5, self.envoyer, [self.chanJeu, "FIN_JOURNEE"])
				serv.execute_delayed(attente+10, self.demarrerMurs, [serv])
		
		#�galit�. Si pas de maire, on refait un autre, sinon c'est lui qui choisit
		elif(self.egalite):
			if(self.maire != None):
				self.statut = "maireDepartage"
				serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "MAIRE_DEPARTAGE", [irclib.nm_to_n(self.maire).capitalize()]])
				serv.execute_delayed(attente + 60, self.maireDepartageLent)
				return
				
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "PREMIERE_EGALITE"])
			serv.execute_delayed(attente, self.annoncerEgalite, [serv])
			
		#Pas d'�galit�, �a roule
		else:
			serv.execute_delayed(attente, self.tuerLapidation, [serv, joueurDesigne])
	
	#Les joueurs peuvent maintenant voter pour les ex-aequo
	def annoncerEgalite(self, serv):
		self.debug(u"Debut prise en compte egalite")
		self.addLog('resultat', "", {'type' : 'egalite'}, 'votes')
		self.addLog('votes', "", {'type' : 'lapidation'}, 'tour')
		self.noVote = self.noVote + 1
		self.statut = "votesLapidation"
		self.votes = {}
		serv.execute_delayed(30, self.faireLapidation, [serv, 0, self.noVote])
	
	#Si le maire est trop lent, on zappe
	def maireDepartageLent(self):
		serv = self.connection
		
		if(self.statut == "maireDepartage"):
			self.envoyer(self.chanJeu, "MAIRE_DEPARTAGE_LENT")
			self.addLog('resultat', "", {'type' : 'maireLent'}, 'votes')
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "FIN_JOURNEE"])
			serv.execute_delayed(10, self.demarrerMurs, [serv])
	
	#Tue le joueur d�sign� par le maire
	def lapidationMaire(self, message):
		if(message in self.joueursEgalite):
			self.statut = "maireDepartageTermine"
			self.addLog('resultat', message, {'type' : 'maire'}, 'votes')
			self.tuerLapidation(self.connection, message)
	
	#Tue le joueur d�sign� par lapidation	
	def tuerLapidation(self, serv, joueurDesigne):
		
		identite = self.identite(self.pseudos[joueurDesigne])
		
		serv.execute_delayed(0, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_1", [joueurDesigne.capitalize()]])           
		serv.execute_delayed(5, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_2", [joueurDesigne.capitalize()]])
		
		if(self.pseudos[joueurDesigne] == self.idiot):
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_ETAIT_IDIOT_1", [joueurDesigne.capitalize()]])
			serv.execute_delayed(20, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_ETAIT_IDIOT_2", [joueurDesigne.capitalize()]])
			
			self.addLog('action', joueurDesigne.capitalize(), {'type' : 'mort', 'typeMort' : 'idiot'}, fils = 'tour')
			
			#S'il s'agissait du maire, on supprime le r�le
			if(self.pseudos[joueurDesigne] == self.maire):
				serv.execute_delayed(30, self.envoyer, [self.chanJeu, "IDIOT_ETAIT_MAIRE", [joueurDesigne.capitalize()]])
				self.addLog('action', joueurDesigne.capitalize(), {'type' : 'finMaire'}, fils = 'tour')
				self.maire = None
				
			self.idiotVote = False
		elif(self.pseudos[joueurDesigne] in self.loups):
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_ETAIT_LOUP", [joueurDesigne.capitalize()]])
			self.addLog('action', joueurDesigne.capitalize(), {'type' : 'mort', 'typeMort' : 'lapidation', 'role' : self.identiteBrute(self.pseudos[joueurDesigne])}, 'tour')
		else:
			serv.execute_delayed(10, self.envoyer, [self.chanJeu, "JOUEUR_DESIGNE_ETAIT_VILLAGEOIS", [joueurDesigne.capitalize(), identite]])
			self.addLog('action', joueurDesigne.capitalize(), {'type' : 'mort', 'typeMort' : 'lapidation', 'role' : self.identiteBrute(self.pseudos[joueurDesigne])}, 'tour')
			
			#Si c'�tait l'ancien, tout le monde perd ses pouvoirs
			if(self.pseudos[joueurDesigne] == self.ancien):
				self.addLog('action', joueurDesigne.capitalize(), {'type' : 'mort', 'typeMort' : 'ancien', 'role' : self.identiteBrute(self.pseudos[joueurDesigne])}, 'tour')
				serv.execute_delayed(15, self.envoyer, [self.chanJeu, "ANCIEN_EST_MORT", [joueurDesigne.capitalize()]])
				self.voyante = "non"	
				self.chasseur = None
				self.salvateur = "non"
				self.salvateurDernier = None
				self.sorciere = "non"
				self.sauvetageSorciere = None
				self.victimeSorciere = None
				self.sauvetageSorciere = None
				self.idiot = None
				self.idiotVote = True
				self.fille = None
				self.policier = None
				self.corbeau = None
				self.victimeCorbeau = None
				self.enPrison = None
				
		#Si c'�tait pas l'idiot, on le tue
		if(self.pseudos[joueurDesigne] != self.idiot):
			#On tue le joueur d�sign�
			joueur = self.pseudos[joueurDesigne]
			self.suivante = self.demarrerMurs
			self.tuer(20, joueur)
		
		#C'�tait l'idiot, on continue normalement
		elif(self.verifierVictoire(35) == 0):
			serv.execute_delayed(40, self.envoyer, [self.chanJeu, "FIN_JOURNEE"])
			serv.execute_delayed(45, self.demarrerMurs, [serv])
				
	#D�marre la phase des murs-murs
	def demarrerMurs(self, serv):
		self.statut = "messageMurs"
		self.messagesMurs = {}
		
		self.addLog('murs', '', fils = 'tour')
		
		self.envoyer(self.chanJeu, "INSTRUCTIONS_MURS")
		serv.execute_delayed(5, self.envoyer, [self.chanJeu, "INSTRUCTIONS_MURS_2"])
		tempsMur = 10*len(self.joueurs) + 5
		if(tempsMur > 65):
			tempsMur = 65
		self.debug(u"Temps mur : " + str(tempsMur)) 
		serv.execute_delayed(tempsMur, self.lireMurs, [serv])
		
	#Ajoute le message sur le mur
	def ajoutMurs(self, serv, source, message):
		#Si le joueur n'a pas d�j� donn� un message, on l'ajoute � la liste
		if (source not in self.messagesMurs):
			#Si le message est trop long, on le coupe
			if(len(message) > 140):
				message = message[0:140] + '...'
			self.messagesMurs[source] = message
			self.addLog('message', message, {'auteur': irclib.nm_to_n(source)}, 'murs')
			
	#Lit les messages ajout�s sur le mur
	def lireMurs(self, serv):
		self.statut = "finMurs"
		self.envoyer(self.chanJeu, "VA_LIRE_MUR")
		
		if(len(self.messagesMurs) == 0):
			serv.execute_delayed(5, self.envoyer, [self.chanJeu, "MUR_VIDE"])
			serv.execute_delayed(10, self.avantPasserNuit, [serv])
		else:
			attente = 5
			for message in random.sample(self.messagesMurs.values(), len(self.messagesMurs)):
				serv.execute_delayed(attente, self.envoyer, [self.chanJeu, '"' + message + '"'])
				attente = attente + 5
			serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "MUR_LU"])
			serv.execute_delayed(attente + 10, self.avantPasserNuit, [serv])
	
	#Deuxi�me v�rification des pr�sents
	def avantPasserNuit(self, serv):
		self.pseudosPresents = []
		serv.who(self.chanJeu)
		self.suivante = self.verifierSpr
		serv.execute_delayed(6, self.tuerAbsents, [serv])
		
	# Fait d�marrer le spiritisme si n�cessaire
	def verifierSpr(self, serv):
		self.suivante = self.passerNuit
		
		self.debug(u"Spritisme ? Jour " + str(self.noJour))
		
		# Tous les deux jours
		if(self.noJour % 2 == 0 and len(self.sprFonctions) > 0):
			self.envoyer(self.chanJeu, "SPR_DEBUT")
			self.statut = "spr"
			self.spr_statut = 0
			self.spr_variables = []
			
			# Choix d'une fonction de spiritisme au hasard
			self.choix_spr = random.sample(self.sprFonctions, 1)[0]
			#self.choix_spr = random.randint(0, len(self.sprFonctions) - 1)
			self.debug(u"Choix de la fonction " + str(self.choix_spr))
			self.connection.execute_delayed(10, self.choix_spr, [serv]) 
			#self.sprFonctions[self.choix_spr](serv)
		else:
			self.suivante(serv)
	
	#Tue la personne en l'enlevant de la liste des joueurs, etc
	def tuer(self, attente, joueur, continuer = True):
		self.debug(u"Mort de " + irclib.nm_to_n(joueur))
		
		if(self.tuteur is not None):
			self.debug("Tuteur = " + self.tuteur)
		
		#Devoice le joueur
		self.connection.execute_delayed(attente, self.connection.mode, [self.chanJeu, "-v " + irclib.nm_to_n(joueur)])
		
		#Si c'est le maire et qu'il reste plus de deux joueurs, on laisse tomber et on y revient plus tard
		if(joueur == self.maire):
			if(len(self.joueurs) > 2):
				self.continuer = continuer
				self.connection.execute_delayed(attente + 10, self.mortMaire)
				return
			else:
				self.maire = None
			
		#Si c'est le chasseur, on laisse tomber et on y revient plus tard
		if(joueur == self.chasseur):
			self.continuer = continuer
			self.connection.execute_delayed(attente + 10, self.chasseurTue)
			return
		
		self.connection.execute_delayed(attente, self.connection.invite, [irclib.nm_to_n(joueur), self.chanParadis])
		self.connection.execute_delayed(attente, self.connection.invite, [irclib.nm_to_n(joueur), self.chanLoups])	
		#Lui envoyer un message pour lui dire
		self.connection.execute_delayed(attente, self.envoyer, [irclib.nm_to_n(joueur), "MESSAGE_AU_MORT", [self.chanParadis, self.chanLoups]])
		
		del self.pseudos[irclib.nm_to_n(joueur).lower()]
		self.joueurs.remove(joueur)
		
		#Retire le joueur de la bonne liste en fonction de son r�le
		
		if(joueur in self.loups):
			self.loups.remove(joueur)
		else:
			self.villageois.remove(joueur)
			
			if(joueur == self.voyante):
				self.voyante = None
				
			elif(joueur == self.chasseur):
				self.chasseur = None
				
			elif(joueur == self.salvateur):
				self.salvateur = None
				self.salvateurDernier = None
			
			elif(joueur == self.sorciere):
				self.sorciere = None
			
			elif(joueur == self.ancien):
				self.ancien = None
				self.ancienResiste = False
			
			elif(joueur == self.idiot):
				self.idiot = None
				
			elif(joueur == self.fille):
				self.fille = None
				
			elif(joueur == self.policier):
				self.policier = None
				self.enPrison = None
				
			elif(joueur == self.corbeau):
				self.corbeau = None
				
			elif(joueur == self.enfant):
				self.enfant = None
				self.tuteur = None
				
			if(joueur == self.traitre):
				self.traitre = None
				
			if(joueur == self.tuteur):
				self.tuteur = None
				self.addLog('action', irclib.nm_to_n(self.enfant), {'type' : 'enfant'}, 'tour')
				self.connection.execute_delayed(attente+5, self.envoyer, [irclib.nm_to_n(self.enfant), "MESSAGE_ENFANT"])
				self.villageois.remove(self.enfant)
				
				self.loups.append(self.enfant)
				self.loupsInconnus[self.enfant] = 'L' + str(self.maxLoups + 1)
				self.maxLoups += 1
				self.debug(self.loupsInconnus)
				self.enfant = None
				
			if(joueur in self.sv):
				self.sv.remove(joueur)
		
		if(joueur == self.victimeCorbeau):
			self.victimeCorbeau = None
		
		if (self.amoureux1 != None):
			self.debug(u"Amoureux1 : " + str(irclib.nm_to_n(self.amoureux1)))
		if (self.amoureux2 != None):
			self.debug(u"Amoureux2 : " + str(irclib.nm_to_n(self.amoureux2)))
			
		if (joueur == self.amoureux1):
			self.connection.execute_delayed(attente + 5, self.tueAmoureux, [self.amoureux2, continuer])
			return
			
		if (joueur == self.amoureux2):
			self.connection.execute_delayed(attente + 5, self.tueAmoureux, [self.amoureux1, continuer])
			return
			
		if (self.secondeVictime != None):
			self.connection.execute_delayed(attente + 5, self.tuer, [0, self.secondeVictime])
			self.secondeVictime = None
			return
			
		if (continuer and self.verifierVictoire(attente) == 0):
			if (self.statut == "lapidationTerminee"):
				self.connection.execute_delayed(attente + 5, self.envoyer, [self.chanJeu, "FIN_JOURNEE"])
			self.connection.execute_delayed(attente + 10, self.suivante, [self.connection])
	
	#Tue l'autre amoureux
	def tueAmoureux(self, amoureux, continuer = True):
		
		self.envoyer(self.chanJeu, "AMOUREUX_MORT", [irclib.nm_to_n(amoureux)])
		identite = self.identite(amoureux)
		if(amoureux in self.loups):
			self.connection.execute_delayed(5, self.envoyer, [self.chanJeu, "AMOUREUX_ETAIT_LOUP", [irclib.nm_to_n(amoureux).capitalize()]])
			
		else:
			self.connection.execute_delayed(5, self.envoyer, [self.chanJeu, "AMOUREUX_ETAIT_VILLAGEOIS", [irclib.nm_to_n(amoureux).capitalize(), identite]])
		
		self.addLog('action', irclib.nm_to_n(amoureux).capitalize(), {'type' : 'mort', 'typeMort' : 'amoureux', 'role' : self.identiteBrute(amoureux)}, 'tour')
		
		self.amoureux1 = None
		self.amoureux2 = None
		self.tuer(10, amoureux, continuer)
	
	#Tue les gens qui ne sont plus pr�sents sur le canal
	def tuerAbsents(self, serv):
		attente = 0
		#Pour chaque joueur qui n'est pas sur le canal
		for joueur in frozenset(self.joueurs):
			self.debug(u"Check " + irclib.nm_to_n(joueur).lower())
			if (irclib.nm_to_n(joueur).lower() not in self.pseudosPresents):
				#On le tue et on lui enl�ve son r�le
				serv.execute_delayed(attente, self.envoyer, [self.chanJeu, "CRISE_CARDIAQUE", [irclib.nm_to_n(joueur)]])
				serv.execute_delayed(attente, self.connection.mode, [self.chanJeu, "-v " + irclib.nm_to_n(joueur)])
				
				del self.pseudos[irclib.nm_to_n(joueur).lower()]
				self.joueurs.remove(joueur)
				self.debug(joueur + " est absent")
				self.debug(self.joueurs)
				
				identite = self.identite(joueur)
				
				self.addLog('action', irclib.nm_to_n(joueur), {'type' : 'mort', 'typeMort' : 'absent', 'role' : self.identiteBrute(joueur)}, 'tour')
				
				if(joueur in self.loups):
					serv.execute_delayed(attente + 10, self.envoyer, [self.chanJeu, "CRISE_CARDIAQUE_LOUP", [irclib.nm_to_n(joueur)]])
					self.loups.remove(joueur)
				else:
					serv.execute_delayed(attente + 10, self.envoyer, [self.chanJeu, "CRISE_CARDIAQUE_VILLAGEOIS", [irclib.nm_to_n(joueur), identite]])
					self.villageois.remove(joueur)
					if(joueur == self.voyante):
						self.voyante = None
						
					elif(joueur == self.chasseur):
						self.chasseur = None
						
					elif(joueur == self.salvateur):
						self.salvateur = None
						self.salvateurDernier = None
						
					elif(joueur == self.ancien):
						self.ancien = None
						self.ancienResiste = False
			
					elif(joueur == self.idiot):
						self.idiot = None
						
					elif(joueur == self.cupidon):
						self.cupidon = None
						
					elif(joueur == self.sorciere):
						self.sorciere = None
						self.sauvetageSorciere = None
						self.victimeSorciere = None
						
					elif(joueur == self.fille):
						self.fille = None
						
					elif(joueur == self.policier):
						self.policier = None
						self.enPrison = None
						
					elif(joueur == self.corbeau):
						self.corbeau = None
						
					if(joueur == self.victimeCorbeau):
						self.victimeCorbeau = None
						
					if(joueur == self.enfant):
						self.enfant = None
						self.tuteur = None
						
					if(joueur == self.tuteur):
						self.tuteur = None
						
					if (joueur == self.amoureux1 or joueur == self.amoureux2):
						self.amoureux1 = None
						self.amoureux2 = None
						
					if (joueur == self.maire):
						self.maire = None
						
					if (joueur == self.traitre):
						self.traitre = None
						
					if(joueur in self.sv):
						self.sv.remove(joueur)
						
				attente = attente + 20
			
		#Si personne n'a gagn�, on ex�cute la fonction suivante
		if(self.verifierVictoire(attente) == 0):
			serv.execute_delayed(attente, self.suivante, [serv])
	
	#Le maire est mort. On lui demande son successeur
	def mortMaire(self):
		self.statut = "mortMaire"
		self.envoyer(self.chanJeu, "MORT_MAIRE", [irclib.nm_to_n(self.maire).capitalize()])
		self.envoyer(irclib.nm_to_n(self.maire), "MESSAGE_MORT_MAIRE")
		self.connection.execute_delayed(60, self.mortMaireLent, [self.maire])
		
	#Le maire est trop lent � d�signer son successeur
	def mortMaireLent(self, ancienMaire):
		if(self.statut == "mortMaire" and ancienMaire == self.maire):
			self.envoyer(self.chanJeu, "MORT_MAIRE_LENT")
			self.addLog('action', "", {'type' : 'successeur'}, 'tour')
			self.maire = None
			self.tuer(5, ancienMaire, self.continuer)
		
	#Le maire annonce son successeur
	def successeurMaire(self, serv, source, message):
		if (message not in self.pseudos or message == irclib.nm_to_n(self.maire).lower()):
			self.envoyer(irclib.nm_to_n(self.maire), "PSEUDO_INCONNU")
		#L'idiot ne peut pas �tre d�sign� s'il a �t� d�masqu�
		elif (self.idiot != None and message == irclib.nm_to_n(self.idiot).lower() and not self.idiotVote):
			self.envoyer(irclib.nm_to_n(self.maire), "SUCCESSEUR_IDIOT", [irclib.nm_to_n(self.idiot).capitalize()])
		else:
			self.statut = "mortMaireFinie"
			self.maire = self.pseudos[message]
			self.envoyer(self.chanJeu, "SUCCESSEUR_MAIRE", [message.capitalize()])
			self.addLog('action', message.capitalize(), {'type' : 'successeur'}, 'tour')
			self.tuer(5, source, self.continuer)
			
	
	#V�rifie si quelqu'un a gagn�
	def verifierVictoire(self, attente):
		self.debug(u"Quelqu'un a gagne ?")
		self.debug(u"Loups : " + str(len(self.loups)))
		self.debug(u"Villageois : " + str(len(self.villageois)))
		
		#Plus personne
		if((len(self.villageois) == 0 and len(self.loups) == 0)):
			self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, "MATCH_NUL"])
			self.connection.execute_delayed(attente+20, self.finir, [self.connection])
			retour = 1
			
			self.addLog('gagnant', 'personne')
			
		#Plus de loups
		elif(len(self.loups) == 0):
			self.debug(u"Etat du traitre : " + str(self.traitre))
			#Pas de traitre ou il reste que le traitre
			if(self.traitre == None or (self.traitre != None and len(self.villageois) == 1)):
				self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, 	"VICTOIRE_VILLAGEOIS"])
				self.connection.execute_delayed(attente+20, self.finir, [self.connection])
				retour = 1
				
				self.addLog('gagnant', 'villageois')
				
			else:
				self.debug(u"Le traitre devient loup")
				
				self.addLog('action', irclib.nm_to_n(self.traitre), {'type' : 'traitre'}, 'tour')
				
				self.connection.execute_delayed(attente+5, self.envoyer, [irclib.nm_to_n(self.traitre), "MESSAGE_TRAITRE"])
				
				self.villageois.remove(self.traitre)
				self.sv.remove(self.traitre)
					
				self.loups.append(self.traitre)
				self.loupsInconnus[self.traitre] = 'L' + str(self.maxLoups + 1)
				self.maxLoups += 1
				self.debug(self.loupsInconnus)
				self.traitre = None
				retour = 0
					
		#Plus aucun villageois
		elif(len(self.villageois) == 0 and (self.victimeSorciere == None or self.victimeSorciere not in self.pseudos)):
			self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, "VICTOIRE_LOUPS_ZERO_VILLAGEOIS"])
			self.connection.execute_delayed(attente+20, self.finir, [self.connection])
			
			self.addLog('gagnant', 'loups_0')
			
			retour = 1
			
		#Un seul villageois et plusieurs loups
		elif(len(self.villageois) == 1 and len(self.loups) > 1):
			# Il reste les amoureux et ils ne sont pas dans le m�me camp
			if (self.amoureux1 != None and self.amoureux2 != None and 
					(self.amoureux1 in self.loups and self.amoureux2 not in self.loups) or
					(self.amoureux1 not in self.loups and self.amoureux2 in self.loups)):
			
				self.debug(u'Les amoureux sont encore en vie')
				retour = 0
			else:
				self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, "VICTOIRE_LOUPS_UN_VILLAGEOIS"])
				self.connection.execute_delayed(attente+20, self.finir, [self.connection])
				self.addLog('gagnant', 'loups_1')
				retour = 1
				
		#Un seul villageois et un seul loup
		elif (len(self.villageois) == 1 and len(self.loups) == 1):
			#Les amoureux gagnent
			if (self.amoureux1 != None and self.amoureux2 != None):
				self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, "VICTOIRE_AMOUREUX"])
				self.connection.execute_delayed(attente+20, self.finir, [self.connection])
				
				self.addLog('gagnant', 'amoureux')
				
				retour = 1
				
			# Conditions sp�ciales (maire, sorci�re, chasseur)
			elif (self.chasseur != None or (self.sorciere != None and self.sorciere != "non" and self.potionMort) or (self.maire != None and self.maire in self.villageois)):
				self.debug(u"Condition speciale")
				self.debug(u"Chasseur : " + str(self.chasseur))
				self.debug(u"Sorciere : " + str(self.sorciere) + " " + str(self.potionMort))
				self.debug(u"Maire : " + str(self.maire) + " " + str(self.maire in self.villageois))
				retour = 0
				
			#Victoire normale
			else:
				self.connection.execute_delayed(attente+10, self.envoyer, [self.chanJeu, "VICTOIRE_LOUPS_UN_VILLAGEOIS"])
				self.connection.execute_delayed(attente+20, self.finir, [self.connection])
				
				self.addLog('gagnant', 'loups_1')
				
				retour = 1
		else:
			retour = 0
			
		self.debug(u"Retour : " + str(retour))
		return retour
	
	#Termine le jeu
	def finir(self, serv, abandon = False):
		if(abandon):
			self.envoyer(self.chanJeu, "ABANDON_PARTIE")
		else:
			self.envoyer(self.chanJeu, "FIN")
			f = open('logs/' + str(datetime.today().strftime('%d_%m_%y_%H_%M_%S')) + '.xml', 'w')
			try:
				f.write(self.log.toxml(encoding = "iso-8859-15"))
			except:
				f.write(self.log.toxml(encoding = "utf-8"))
			f.close()
			del self.log
			
		serv.execute_delayed(2, serv.mode, [self.chanJeu, "-m"])
		serv.execute_delayed(2, serv.mode, [self.chanJeu, "-N"])
		serv.execute_delayed(5, serv.mode, [self.chanLoups, "-i"])
		serv.execute_delayed(5, serv.mode, [self.chanLoups, "-m"])
		serv.execute_delayed(5, serv.mode, [self.chanParadis, "-i"])
		for joueur in self.joueurs :
			serv.mode(self.chanJeu, " -v " + irclib.nm_to_n(joueur))
			
		self.statut = "attente"
		self.demarre = False
	
	# Chuchotement
	def chuchoter(self, serv, source, message, messageNormal):
		self.debug(u"Chuchotement de " + source)
		
		expediteur = irclib.nm_to_n(source)
		
		messageSplit = message.split(" ", 2)
		messageNormalSplit = messageNormal.split(" ", 2)
		
		# Si pas tous les arguments
		if(len(messageSplit) < 3):
			self.envoyer(expediteur, "ERREUR_CHUCHOTER", [self.declencheurs["chuchoter"]])
		else:
			destinataire = messageSplit[1]
			
			# Envoi du chuchotement
			if(destinataire not in self.pseudos):
				self.debug(u"Pseudo inconnu")
				self.envoyer(expediteur, "PSEUDO_INCONNU")
				return
				
			destinataire = irclib.nm_to_n(self.pseudos[destinataire])
			
			if(expediteur == destinataire):
				self.debug(u"Se parle � lui-m�me")
				self.envoyer(expediteur, "PSEUDO_INCONNU")
				return
			else:
				self.debug(u"Chuchotement pour " + destinataire + ", message : " + messageNormalSplit[2])
				self.envoyer(expediteur, "CHUCHOTEMENT_CONFIRMATION", [destinataire])
				self.envoyer(destinataire, "CHUCHOTEMENT_ENVOI", [expediteur, messageNormalSplit[2]])
			
			# Calcul probabilit� d'echec
			proba = self.whisperProbaJoueurs[source]
			self.debug(u"Proba " + str(proba))
			
			chance = self.whisperProba[proba] / (100.0)
			self.debug(u"Chance " + str(chance))
			
			essai = random.random()
			self.debug(u"Essai " + str(essai))
			
			#Echec
			if(essai <= chance):
				essaiExpediteur = random.random()
				self.debug(u"Essai expediteur " + str(essaiExpediteur))
				
				if(essaiExpediteur > 0.15):
					self.envoyer(self.chanJeu, "CHUCHOTEMENT_ECHEC", [expediteur, messageNormalSplit[2]])
					self.addLog('action', messageNormalSplit[2], {'type': 'chuchotement', 'echec': '1', 'expediteur': expediteur, 'destinataire': destinataire}, 'tour')
				else:
					self.envoyer(self.chanJeu, "CHUCHOTEMENT_ECHEC_2", [expediteur, destinataire, messageNormalSplit[2]])
					self.addLog('action', messageNormalSplit[2], {'type': 'chuchotement', 'echec': '2', 'expediteur': expediteur, 'destinataire': destinataire}, 'tour')
					
				self.whisperProbaJoueurs[source] = 0
			else:
				self.addLog('action', messageNormalSplit[2], {'type': 'chuchotement', 'echec': '0', 'expediteur': expediteur, 'destinataire': destinataire}, 'tour')
				
				# Augmentation de la probabilit� d'�chec
				proba += 1
				
				if(proba < len(self.whisperProba)):
					self.whisperProbaJoueurs[source] += 1
					
			self.debug(u"New chance : " + str(self.whisperProbaJoueurs[source]))
	
	#############
	# SPIRITISME
	
	# Deux joueurs dans le m�me camp
	def spr_memeCamp(self, serv, source = None, message = None):
		try:
			# Demande du premier pseudo
			if(self.spr_statut == 0):
				self.envoyer(self.chanJeu, "SPR_MEMECAMP_0")
				self.spr_statut = 1
				
			# Enregistrement du premier pseudo et demande du second	
			elif(self.spr_statut == 1):
				if(message in self.pseudos):
					self.spr_variables.append(message)
					self.envoyer(self.chanJeu, "SPR_MEMECAMP_1")
					self.spr_statut = 2
			
			# Donne la r�ponse
			elif(self.spr_statut == 2):
				if(message in self.pseudos and message != self.spr_variables[0]):
					self.spr_variables.append(message)
					
					premier = self.pseudos[self.spr_variables[0]]
					second = self.pseudos[self.spr_variables[1]]
					
					if((premier in self.loups and second in self.loups) or (premier in self.villageois and second in self.villageois)):
						self.addLog('spr', irclib.nm_to_n(premier) + ';' + irclib.nm_to_n(second), {'type' : 'memecamp', 'resultat' : 'identique'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_MEMECAMP_2", [irclib.nm_to_n(premier), irclib.nm_to_n(second)])
					else:
						self.addLog('spr', irclib.nm_to_n(premier) + ';' + irclib.nm_to_n(second), {'type' : 'memecamp', 'resultat' : 'different'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_MEMECAMP_3", [irclib.nm_to_n(premier), irclib.nm_to_n(second)])
						
					self.spr_statut = 3
					self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
				
	# Connaitre le nombre de r�les particuliers restants
	def spr_nombreRoles(self, serv, source = None, message = None):
		try:
			# Demande de la cat�gorie
			if(self.spr_statut == 0):
				self.envoyer(self.chanJeu, "SPR_NOMBREROLES_0")
				self.spr_statut = 1
				
			# Envoi du nombre
			elif(self.spr_statut == 1):
				if(message == "1" or message == "2" or message == "3"):
					self.spr_statut = 2
					if(message == "1"):
						self.addLog('spr', str(len(self.loups)), {'type' : 'nombreroles', 'resultat' : 'loup'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_NOMBREROLES_1", [str(len(self.loups))])
					elif(message == "2"):
						self.addLog('spr', str(len(self.sv)), {'type' : 'nombreroles', 'resultat' : 'sv'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_NOMBREROLES_2", [str(len(self.sv))])
					elif(message == "3"):
						nombre = len(self.joueurs) - (len(self.loups) + len(self.sv))
						self.addLog('spr', str(nombre), {'type' : 'nombreroles', 'resultat' : 'speciaux'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_NOMBREROLES_3", [str(nombre)])
					self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
								
	# Savoir si un r�le existe
	def spr_roleExiste(self, serv, source = None, message = None):
		try:
			# Demande du r�le
			if(self.spr_statut == 0):
				self.envoyer(self.chanJeu, "SPR_ROLEEXISTE_0")
				self.spr_statut = 1
				
			# Envoi du r�le
			elif(self.spr_statut == 1):
				if(message == "1" or message == "2" or message == "3" or message == "4"):
					self.spr_statut = 2
					
					if(message == "1"):
						role = self.fille
						index = "fille"
					elif(message == "2"):
						role = self.ancien
						index = "ancien"
					elif(message == "3"):
						role = self.chasseur
						index = "chasseur"
					elif(message == "4"):
						role = self.idiot
						index = "idiot"
					
					if(index in self.roles):
						roleDemande = self.roles[index]
					else:
						roleDemande = self.rolesDefault[index]
					
					if(not role):
						self.addLog('spr', 'non', {'type' : 'roleexiste', 'resultat' : index}, 'tour')
						self.envoyer(self.chanJeu, "SPR_ROLEEXISTE_1", [roleDemande])
					else:
						self.addLog('spr', 'oui', {'type' : 'roleexiste', 'resultat' : index}, 'tour')
						self.envoyer(self.chanJeu, "SPR_ROLEEXISTE_2", [roleDemande])
						
					self.spr_terminer(serv)
						
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
			
	# Savoir si la sorci�re a un pseudo entre A et M
	def spr_sorcierePseudo(self, serv, source = None, message = None):
		try:
			if(self.spr_statut == 0):
				self.spr_statut = 1
				
				if(not self.sorciere or self.sorciere == "non"):
					self.addLog('spr', 'aucune', {'type' : 'sorcierepseudo'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_PSEUDOSORCIERE_0")
				elif(irclib.nm_to_n(self.sorciere).lower() <= 'm'):
					self.addLog('spr', 'oui', {'type' : 'sorcierepseudo'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_PSEUDOSORCIERE_1")
				else:
					self.addLog('spr', 'non', {'type' : 'sorcierepseudo'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_PSEUDOSORCIERE_2")
					
				self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
	
	# Savoir si les loups ont un pseudo entre A et M
	def spr_loupsPseudo(self, serv, source = None, message = None):
		try:
			if(self.spr_statut == 0):
				self.spr_statut = 1
				entre = False
				
				for loup in self.loups:
					if(irclib.nm_to_n(loup).lower()[0] <= 'm'):
						entre = True
				
				if(entre):
					self.addLog('spr', 'oui', {'type' : 'loupsPseudo'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_LOUPSPSEUDO_0")
				else:
					self.addLog('spr', 'non', {'type' : 'loupsPseudo'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_LOUPSPSEUDO_1")
					
				self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
	
	# Savoir si le maire est simple villageois
	def spr_maireSV(self, serv, source = None, message = None):
		try:
			if(self.spr_statut == 0):
				self.spr_statut = 1
				
				if(not self.maire):
					self.addLog('spr', 'aucun', {'type' : 'mairesv'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_MAIRESV_0")
				elif(self.maire in self.sv):
					self.addLog('spr', 'oui', {'type' : 'mairesv'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_MAIRESV_1")
				else:
					self.addLog('spr', 'non', {'type' : 'mairesv'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_MAIRESV_2")
					
				self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
			
	# Savoir si la voyante a d�j� vu un LG
	def spr_voyanteLoup(self, serv, source = None, message = None):
		try:
			if(self.spr_statut == 0):
				self.spr_statut = 1
				
				if(self.voyanteObserveLoup):
					self.addLog('spr', 'oui', {'type' : 'voyanteloup'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_VOYANTELOUP_0")
				else:
					self.addLog('spr', 'non', {'type' : 'voyanteloup'}, 'tour')
					self.envoyer(self.chanJeu, "SPR_VOYANTELOUP_1")
					
				self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
	
	# Savoir si quelqu'un est un SV
	def spr_estSV(self, serv, source = None, message = None):
		try:
			# Demande du pseudo
			if(self.spr_statut == 0):
				self.envoyer(self.chanJeu, "SPR_ESTSV_0")
				self.spr_statut = 1
			
			# Donne la r�ponse
			elif(self.spr_statut == 1):
				if(message in self.pseudos):
					
					joueur = self.pseudos[message]
					
					if(joueur in self.sv):
						self.addLog('spr', irclib.nm_to_n(joueur), {'type' : 'estSV', 'resultat': 'oui'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_ESTSV_1", [irclib.nm_to_n(joueur)])
					else:
						self.addLog('spr', irclib.nm_to_n(joueur), {'type' : 'estSV', 'resultat': 'non'}, 'tour')
						self.envoyer(self.chanJeu, "SPR_ESTSV_2", [irclib.nm_to_n(joueur)])
						
					self.spr_statut = 2
					self.spr_terminer(serv)
		except:
			self.envoyer(self.chanJeu, u"S�ance annul�e, probl�me de connexion avec les morts.")
			self.debug(u"Erreur spiritisme ! " + str(sys.exc_info()[1]))
			self.spr_statut = 99
			self.spr_terminer(serv)
	
	# Termine le spiritisme et passe � la suite
	def spr_terminer(self, serv):
		self.sprFonctions.remove(self.choix_spr)
		self.connection.execute_delayed(15, self.envoyer, [self.chanJeu, "SPR_TERMINE"])
		self.connection.execute_delayed(20, self.suivante, [self.connection])
	
	#############
	# FONCTIONS IRC
	
	#Pseudo d�j� utilis�
	def on_nicknameinuse(self, serv, ev):
		serv.nick(self.pseudo + str(random.randint(0, 1000)))
		
	#Lors de la connexion au serveur
	def on_welcome(self, serv, ev):
		self.debug(u"Connecte avec le pseudo " + serv.get_nickname())
		#A-t-on le bon pseudo ?
		if(serv.get_nickname() != self.pseudo):
			self.envoyer("nickserv", "recover " + self.pseudo + " " + self.mdp, gras = False)
			self.envoyer("nickserv", "release " + self.pseudo + " " + self.mdp, gras = False)
			serv.nick(self.pseudo)
			
		#Identification
		self.envoyer("nickserv",  "identify " + self.mdp, gras = False)
		self.debug(u"Connecte avec le pseudo " + serv.get_nickname())
		
		#Nettoie les canaux
		self.envoyer("chanserv", "clear " + self.chanParadis + " users", gras = False)
		self.envoyer("chanserv", "clear " + self.chanLoups + " users", gras = False)
		
		#Connexion aux canaux
		serv.join(self.chanJeu)
		serv.execute_delayed(5, serv.join, [self.chanParadis])
		serv.execute_delayed(5, serv.join, [self.chanLoups])
		
		#Modes
		serv.execute_delayed(5, serv.mode, [self.chanLoups, "+m"])
		serv.execute_delayed(5, serv.mode, [self.chanJeu, "-m"])
		serv.execute_delayed(5, serv.mode, [self.chanJeu, "-N"])
	
	#R�ception d'un message
	def on_pubmsg(self, serv, ev):
		self.traiterMessage(serv, ev)
		
	#R�ception d'un message priv�
	def on_privmsg(self, serv, ev):
		self.traiterMessagePrive(serv, ev)
	
	#R�ception d'une notice priv�e
	def on_privnotice(self, serv, ev):
		try:
			self.debug(irclib.nm_to_n(ev.source()) + " >>> " + ev.arguments()[0])
		except:
			self.debug(u"Notice inconnue")
			
		# Si c'est un knock
		notice = ev.arguments()[0].split()
		
		if(notice[0] == "[Knock]"):
			canal = ev.target().replace('@', '')
			joueur = notice[2]
			
			self.debug(u"Knock de " + joueur + " sur " + canal)
			
			# Si ce n'est pas un joueur et qu'on est en jeu
			if(joueur not in self.joueurs and self.demarre):
				self.debug(irclib.nm_to_n(joueur) + " invite sur " + canal)
				serv.invite(irclib.nm_to_n(joueur), canal)
			else:
				self.debug(irclib.nm_to_n(joueur) + " non invite sur " + canal + " !")
			
		
	
	#R�ception d'un who
	def on_whoreply(self, serv, ev):
		self.pseudosPresents.append(ev.arguments()[4].lower())
	
	#Quelqu'un a rejoint un canal
	def on_join(self, serv, ev):

		self.debug(ev.source() + " a rejoint " + ev.target())

		#Si c'est nous, �a compte pas...
		if(irclib.nm_to_n(ev.source()) == self.pseudo):
			return 0
		
		#Canal du jeu
		elif(ev.target().lower() == self.chanJeu.lower()):
			
			#S'il s'agit d'un joueur encore en vie, on le voice
			if (ev.source() in self.joueurs):
				serv.mode(self.chanJeu, "+v " + irclib.nm_to_n(ev.source()))
		
		#Canal des loups
		elif(ev.target().lower() == self.chanLoups.lower() and self.statut != "attente"):
			
			#S'il s'agit bien d'un loup (et non d'un mort)
			if(ev.source() in self.loups):
				serv.mode(self.chanLoups, "+v " + irclib.nm_to_n(ev.source()))
				self.loupsSurCanal = self.loupsSurCanal + 1
				
				#Si c'est le premier loup sur le canal
				if(self.loupsSurCanal == 1):
					self.aParlerLoup = True
					self.statut = "traiterCanalLoups"
					serv.execute_delayed(5, self.envoyer, [self.chanLoups, "INSTRUCTIONS_LOUPS", [self.declencheurs['tuerLoups']]])
	
	# Quelqu'un sur le paradis demande les r�les
	def envoyerRolesAutresJoueurs(self, source):
		try:
			listeRoles = ""
		
			for joueur in self.joueurs:
				pseudo = irclib.nm_to_n(joueur)
				listeRoles += pseudo + ' : ' + self.identite(joueur) + ". "
			
			self.envoyer(irclib.nm_to_n(source), listeRoles)
		except:
			self.debug(u"Erreur envoyerRolesAutresJoueurs")
	
	#Un joueur a chang� de nick. Si on est en jeu, on doit le changer partout
	def on_nick(self, serv, ev):
		if(self.statut != "attente"):
			ancienPseudo = irclib.nm_to_n(ev.source()).lower()
			ancienDomaine = ev.source()
			nouveauPseudo = ev.target().lower()
			nouveauDomaine = ev.target() + "!" + irclib.nm_to_uh(ev.source())
			
			self.debug(ancienPseudo + " a change son pseudo en " + nouveauPseudo)
			self.debug(u"De " + ancienDomaine + " a " + nouveauDomaine)
			
			#Il s'agit d'un joueur
			if(ancienDomaine in self.joueurs):				
				del self.pseudos[ancienPseudo]
				self.pseudos[nouveauPseudo] = nouveauDomaine
				
				self.joueurs.remove(ancienDomaine)
				self.joueurs.append(nouveauDomaine)
				
				if(ancienDomaine in self.loups):
					self.loups.remove(ancienDomaine)
					self.loups.append(nouveauDomaine)
				elif(ancienDomaine in self.villageois):
					self.villageois.remove(ancienDomaine)
					self.villageois.append(nouveauDomaine)
					
				if(ancienDomaine in self.loupsInconnus):
					self.debug(self.loupsInconnus)
					self.loupsInconnus[nouveauDomaine] = self.loupsInconnus[ancienDomaine]
					del self.loupsInconnus[ancienDomaine]
					self.debug(self.loupsInconnus)
		
				#R�les sp�ciaux
				if(self.voyante == ancienDomaine):
					self.voyante = nouveauDomaine
					
				if(self.chasseur == ancienDomaine):
					self.chasseur = nouveauDomaine
					
				if(self.salvateur == ancienDomaine):
					self.salvateur = nouveauDomaine
					
				if(self.salvateurDernier == ancienDomaine):
					self.salvateurDernier = nouveauDomaine
					
				if(self.idiot == ancienDomaine):
					self.idiot = nouveauDomaine
					
				if(self.ancien == ancienDomaine):
					self.ancien = nouveauDomaine
					
				if(self.cupidon == ancienDomaine):
					self.cupidon = nouveauDomaine
					
				if(self.sorciere == ancienDomaine):
					self.sorciere = nouveauDomaine
					
				if(self.policier == ancienDomaine):
					self.policier = nouveauDomaine
					
				if(self.enPrison == ancienDomaine):
					self.enPrison = nouveauDomaine
					
				if(self.corbeau == ancienDomaine):
					self.corbeau = nouveauDomaine
					
				if(self.victimeCorbeau == ancienDomaine):
					self.victimeCorbeau = nouveauDomaine
					
				if(self.enfant == ancienDomaine):
					self.enfant = nouveauDomaine
					
				if(self.tuteur == ancienDomaine):
					self.tuteur = nouveauDomaine
					
				if(self.victimeLoups == ancienPseudo):
					self.victimeLoups = nouveauPseudo
					
				if(self.victimeSorciere == ancienPseudo):
					self.victimeSorciere = nouveauPseudo
					
				if(self.sauvetageSorciere == ancienPseudo):
					self.sauvetageSorciere = nouveauPseudo
					
				if(self.fille == ancienDomaine):
					self.fille = nouveauDomaine
					
				if(self.amoureux1 == ancienDomaine):
					self.amoureux1 = nouveauDomaine
					
				if(self.amoureux2 == ancienDomaine):
					self.amoureux2 = nouveauDomaine
					
				if(self.maire == ancienDomaine):
					self.maire = nouveauDomaine
				
				if(self.traitre == ancienDomaine):
					self.traitre = nouveauDomaine

toFile = False
if(len(sys.argv) > 1):
	if(sys.argv[1] == '-r'):
		toFile = True
		f = codecs.open('./log.txt', 'w', 'utf-8', 'ignore');
		sys.stdout = f

bot = Bot()

print sys.stdout.encoding 
try:
	bot.start()
except KeyboardInterrupt:
	if(toFile):
		sys.stdout = sys.__stdout__
		f.close()
	bot.connection.disconnect("Le maitre du jeu se retire...")
        bot.connection.close()
except:
	if(toFile):
		sys.stdout = sys.__stdout__
		f.close()
	bot.erreur(sys.exc_info()[1])
	print(sys.exc_info()[1])
	traceback.print_exc()
	bot.connection.disconnect(u"Le maitre du jeu se retire apr�s avoir plant�...")
        bot.connection.close()

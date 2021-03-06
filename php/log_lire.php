<?php
function role($role)
{
	switch($role)
	{
		case 'loup':
			return 'un loup garou';
			
		case 'villageois':
			return 'un villageois';
			
		case 'voyante':
			return 'la voyante';
			
		case 'chasseur':
			return 'le chasseur';
			
		case 'idiot':
			return 'l\'idiot du village';
			
		case 'salvateur':
			return 'le salvateur';
			
		case 'ancien':
			return 'l\'ancien';
			
		case 'cupidon':
			return 'Cupidon';

		case 'ange':
			return 'l\'ange';
			
		case 'fille':
			return 'la petite fille';
			
		case 'sorciere':
			return 'la sorcière';
			
		case 'policier':
			return 'le policier';
			
		case 'corbeau':
			return 'le corbeau';

		case 'maitre':
			return 'le maître-chanteur';
			
		case 'enfant':
			return 'l\'enfant loup';
	}
}

function vraiPseudo($pseudo)
{
	global $joueurs;
	
	foreach($joueurs as $joueur)
	{
		if(strcasecmp($pseudo, $joueur) == 0)
		{
			return '<span class="pseudoJoueur" title="'. role($joueur["role"]). '">'. strval($joueur) .'</span>';
		}
	}
	
	return strval($pseudo);
}

function vraiPseudoRaw($pseudo)
{
	global $joueurs;
	
	foreach($joueurs as $joueur)
	{
		if(strcasecmp($pseudo, $joueur) == 0)
		{
			return strval($joueur);
		}
	}
	
	return strval($pseudo);
}

function traiterAction($noeud)
{
	global $joueurs;
	
	switch($noeud['type'])
	{
		case('cupidon'):
			$amoureux = explode(';', $noeud);
			echo 'Cupidon rend ' . vraiPseudo($amoureux[0]) . ' et ' . vraiPseudo($amoureux[1]) . ' amoureux !';
			break;
			
		case('policier'):
			echo 'Le policier met ' . vraiPseudo($noeud) . ' en prison.';
			break;
			
		case('corbeau'):
			echo 'Le corbeau attribue deux voix à ' . vraiPseudo($noeud) . '.';
			break;
			
		case('voyante'):
			echo 'La voyante observe ' . vraiPseudo($noeud) . ', ' . role($noeud['role']) . '.';
			if(role($noeud['role']) == 'l\'enfant loup')
				echo ' Cependant, elle le voit comme un simple villageois.';
			break;
			
		case('salvateur'):
			echo 'Le salvateur protège ' . vraiPseudo($noeud) . '.';
			break;
		
		case('loup'):
			if($noeud == '')
				echo 'Les loups ne choisissent aucune victime.';
			else
				echo 'Les loups décident de tuer ' . vraiPseudo($noeud) . '.';
			break;
			
		case('sorciereVie'):
			echo 'La socière utilise sa potion pour ramener ' . vraiPseudo($noeud) . ' à la vie.';
			break;
			
		case('sorciereMort'):
			echo 'La sorcière utilise sa potion pour empoisonner ' . vraiPseudo($noeud) .'.';
			break;
			
		case('mort'):
			traiterMort($noeud);
			break;
			
		case('finMaire'):
			echo $noeud . ' n\'est donc plus maire !';
			break;
		
		case('successeur'):
			if($noeud == '')
				echo 'Le maire ne parvient pas à choisir de successeur...';
			else
				echo vraiPseudo($noeud) . ' est le nouveau maire !';
			break;
				
		case('traitre'):
			echo $noeud . ' est un traitre...et devient maintenant un loup-garou !';
			$joueurs[vraiPseudoRaw($noeud)]['role'] = 'loup';
			break;
			
		case('chuchotement'):
			echo '<strong>' . $noeud['expediteur'] . '</strong> chuchote à <strong>' . $noeud['destinataire'] . '</strong> : "' . $noeud . '"';
			
			switch($noeud['echec'])
			{
				case('1'):
					echo '. Mais ' . $noeud['expediteur'] . ' n\'est pas assez discret et tout le monde entend son message !'; 
					break;
				case('2');
					echo '. Mais ' . $noeud['expediteur'] . ' n\'est pas assez discret et tout le monde entend son message et voit à qui il parlait !';
					break;
			}
			
			break;
		
		case('enfant'):
			echo $noeud . ', l\'enfant loup, devient un vrai loup-garou !';
			$joueurs[vraiPseudoRaw($noeud)]['role'] = 'loup';
			break;

		case('chantage'):
			echo 'Le maître-chanteur décide de menacer ' . vraiPseudo($noeud) . '.';
			break;
		
		default:
			echo 'Quelque chose d\'étrange s\'est passé !';
	}
	echo '<br />';
}

function traiterVotes($noeud)
{
	if($noeud['type'] == 'maire')
	{
		echo '<h3>Élection du maire</h3>';
		
		if(isset($noeud->vote))
		{
			
			echo '<ul>';
			
			echo '<li style="clear: both;"><div style="width: 300px; float: left;"><strong>Votant</strong></div><div><strong>Vote</strong></div></li>';
			foreach($noeud->vote as $vote)
				echo '<li style="clear: both;"><div style="width: 300px; float: left;">' . vraiPseudo(strtok($vote, '!')) . '</div><div>' . vraiPseudo($vote['pour']) . '</div></li>';
			
			echo '</ul>';
		}
		
		echo 'Résultat de l\'élection : ';
		
		switch($noeud->resultat['type'])
		{
			case('aucun'):
				echo 'Aucun maire n\'est élu !';
				break;
			
			case('majorite'):
				echo vraiPseudo($noeud->resultat) . ' est élu à la majorité.';
				break;
				
			case('egalite'):
				echo 'Égalité, ' . vraiPseudo($noeud->resultat) . ' devient maire.'; 
				break;
		}
	}
	elseif($noeud['type'] == 'lapidation')
	{
		global $secondTour;
		if($secondTour)
			echo '<h3>Lapidation (second tour)</h3>';
		else
		{
			echo '<h3>Lapidation</h3>';
			$secondTour = true;
		}
		
		if(isset($noeud->votant))
		{
			echo '<ul>';
		
			echo '<li style="clear: both;"><div style="width: 300px; float: left;"><strong>Votant</strong></div><div><strong>Vote</strong></div></li>';
			foreach($noeud->votant as $vote)
			{
				if($vote == 'corbeau1' || $vote == 'corbeau2')
					$votant = 'Vote du corbeau';
				else
					$votant = strtok($vote, '!');
					
				if(! empty($vote['vote']))
					$voteContre = vraiPseudo($vote['vote']);
				else
					$voteContre = "<i>Blanc</i>";

				echo '<li style="clear: both;"><div style="width: 300px; float: left;">' . vraiPseudo($votant) . '</div><div>' . $voteContre . '</div></li>';
			}
			
			echo '</ul>';
		}
		
		echo 'Résultat du vote : ';
		
		switch($noeud->resultat['type'])
		{			
			case('maire'):
				echo 'Le maire décide de tuer ' . vraiPseudo($noeud->resultat) . '. ';
				break;
				
			case('maireLent'):
				echo 'Le maire n\'est pas parvenu à choisir !';
				break;
				
			case('egalite'):
				echo 'Égalité !';
				break;
		}
	}
	
	echo '<br /><br />';
}

function traiterMurs($noeud)
{
	echo '<h3>Murs-Murs</h3>';
	
	if(!isset($noeud->message))
		echo 'Aucun message n\'a été laissé sur le mur !';
	
	foreach($noeud->message as $message)
	{
		echo '<strong>'.$message['auteur'].' : </strong>';
		echo '"' . htmlentities(wordwrap($message, 75, ' ', true), ENT_QUOTES, 'UTF-8') . '"<br />';
	}
	
	echo '<br />';
}

function traiterSpr($noeud)
{
	echo '<h3>Séance de spiritisme</h3>';
	
	echo '<p>Les morts l\'ont dit : ';
	
	switch($noeud['type'])
	{			
		case('memecamp'):
			$personnes = explode(';', $noeud);
			$premier = vraiPseudo($personnes[0]);
			$second = vraiPseudo($personnes[1]);
			
			if($noeud['resultat'] == 'identique')
				echo $premier . ' et ' . $second . ' sont dans le même camp.';
			else
				echo $premier . ' et ' . $second . ' ne sont pas dans le même camp.';
			
			break;
			
		case('nombreroles'):
			
			if($noeud['resultat'] == 'loup')
				echo 'des loups, il y en a encore ' . $noeud . '.';
			elseif($noeud['resultat']== 'sv')
				echo 'des simples villageois, il y en a encore ' . $noeud . '.';
			elseif($noeud['resultat']== 'speciaux')
				echo 'des villageois aux pouvoirs spéciaux, il y en a encore ' . $noeud . '.';
			
			break;
			
		case('roleexiste'):
			
			if(strval($noeud) == 'oui')
				echo 'il y a ' . role($noeud['resultat']) . ' dans le village.';
			else
				echo role($noeud['resultat']) . ' ne fait pas partie du village.';
			
			break;
			
		case('sorcierepseudo'):
			
			if(strval($noeud) == 'aucune')
				echo 'sans sorcière dans le village, ils ne peuvent rien dire sur son pseudo !';
			elseif(strval($noeud) == 'oui')
				echo 'la première lettre du pseudo de la sorcière est entre A et M.';
			else
				echo 'la première lettre du pseudo de la sorcière n\'est pas entre A et M.';
			
			break;
			
		case('loupsPseudo'):
			
			if(strval($noeud) == 'oui')
				echo 'il y a un ou plusieurs loups dont la première lettre du pseudo est entre A et M.';
			else
				echo 'aucun loup n\'a la première lettre de son pseudo entre A et M.';
			
			break;
			
		case('mairesv'):
			
			if(strval($noeud) == 'aucun')
				echo 'ils ne connaissent pas le statut du maire, puisqu\'il n\'y en a pas !';
			elseif(strval($noeud) == 'oui')
				echo 'le maire est un simple villageois.';
			else
				echo 'le maire n\'est pas un simple villageois...ami, ou ennemi ?';
			
			break;
			
		case('voyanteloup'):
			
			if(strval($noeud) == 'oui')
				echo 'la voyante a découvert l\'identité d\'au moins un loup !';
			else
				echo 'la voyante n\'a découvert aucun loup...';
			
			break;
			
		case('estSV'):
			
			if($noeud['resultat'] == 'oui')
				echo vraiPseudo($noeud) . ' est un simple villageois.';
			else
				echo vraiPseudo($noeud) . ' possède des pouvoirs spéciaux...mais quel genre de pouvoir ?';
			
			break;
	}
	
	echo '</p>';
}

function traiterMort($noeud)
{
	global $joueurs;
	
	switch($noeud['typeMort'])
	{
		case('nuit'):
			echo vraiPseudo($noeud) . ', '.role($noeud['role']).', meurt pendant la nuit.';
			retirerJoueur($noeud);
			break;
			
		case('chasseur'):
			echo 'Le chasseur décide de tuer ' . vraiPseudo($noeud) . ', qui était '.role($noeud['role']). '.';
			retirerJoueur($noeud);
			break;
			
		case('idiot'):
			echo vraiPseudo($noeud) . ' étant l\'idiot du village, il est épargné.';
			break;
			
		case('lapidation'):
			echo vraiPseudo($noeud) . ', '.role($noeud['role']).', se fait lapider par les villageois.';
			retirerJoueur($noeud);
			break;
			
		case('ancien'):
			echo vraiPseudo($noeud) . ' étant l\'ancien, les joueurs perdent leurs pouvoirs !';
			break;
			
		case('amoureux'):
			echo vraiPseudo($noeud) . ', ' . role($noeud['role']) . ', suit son amour dans la mort.';
			retirerJoueur($noeud);
			break;
			
		case('absent'):
			echo vraiPseudo($noeud) . ', ' . role($noeud['role']) . ', meurt suite à une crise cardiaque.';
			retirerJoueur($noeud);
			break;
		
		default:
			echo 'Personne n\'est mort cette nuit !';
	}
}

function retirerJoueur($noeud)
{
	global $joueurs;
	$pseudoRetirer = strval($noeud);

	foreach ($joueurs as $pseudo => $joueur)
	{
		if(strcasecmp($pseudoRetirer, $pseudo) == 0)
			unset($joueurs[$pseudo]);
	}
}

if(!isset($_GET['log']))
{
	die("Erreur : log non spécifié");
}

$logName = $_GET['log'];

if(preg_match("#^[0-9]+_[0-9]+_[0-9]+_[0-9]+_[0-9]+_[0-9]+$#", $logName) != 1)
{
	die('Nope.');
}

$log = @simplexml_load_file('./logs/' . $logName . '.xml');

if($log === false)
{
	$logRaw = @file_get_contents('./logs/' . $logName . '.xml');

	// Retirer les caractères Unicode invalides
	// http://www.phpwact.org/php/i18n/charsets
	preg_replace('/[^\x{0009}\x{000a}\x{000d}\x{0020}-\x{D7FF}\x{E000}-\x{FFFD}]+/u', ' ', $logRaw);
	$log = simplexml_load_string($logRaw);

	if($log === false)
	{
		die('Erreur d\'ouverture du log.');
	}
}

$date = $log->date;
?>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr">
	<head>
		<title>Loups-Garous - Partie du <?php echo $date; ?></title>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
		<style type="text/css">
		body
		{
			background-color: #EEEEFF;
			padding: 10px;
		}
		
		#header
		{
			width: 60%;
			margin: auto;
			text-transform: uppercase;
			border: 2px solid black;
			text-align: center;
			font-size: x-large;
			background-color: white;
		}
		
		ul
		{
			list-style-type: none;
		}
		
		#chat
		{
			width: 95%;
			height: 768px;
			
			background-color: white;
			border: 1px solid black;
			overflow: auto;
			padding-left: 5px;
		}
		
		.mp
		{
			color: gray;
		}
		
		.loupsgarous
		{
			color: #900000;
		}

		.pseudoJoueur
		{
			text-decoration: underline dotted;
			cursor: default;
		}
		</style>
	</head>
	<body>
	<div id="header"><p>Partie du <?php echo $date; ?></p></div>
	
	<p><a href="log.php">Retour aux autres parties</a></p>
	
	<p><strong>Personnalité : </strong><?php echo $log->personnalite; ?></p>
	<p><strong>Joueurs :</strong></p>
		<ul>
		<?php
		
		$traitre = $log->xpath('//tour/action[@type="traitre"]');
		
		if(empty($traitre))
			$traitre = '';
		else
			$traitre = $traitre[0];
		
		$joueurs = array();
		
		// Évite les doublons
		foreach($log->joueurs->joueur as $joueur)
		{
			$tempJoueurs[strval($joueur)] = $joueur;
		}

		foreach($tempJoueurs as $joueur)
		{
			$joueurs[strval($joueur)] = $joueur;
			
			if(strval($traitre) == strval($joueur))
				echo '<li style="clear: both;"><div style="width: 300px; float: left;">'.$joueur.'</div><div style="float: left;">' . role($joueur['role']) . ' (traître)</div></li>';
			else if(strval($joueur['role']) == 'enfant')
			{
				$tuteur = $log->tuteur;
				echo '<li style="clear: both;"><div style="width: 300px; float: left;">'.$joueur.'</div><div style="float: left;">' . role($joueur['role']) . ' (tuteur : '.$tuteur.')</div></li>';
			}
			else
				echo '<li style="clear: both;"><div style="width: 300px; float: left;">'.$joueur.'</div><div style="float: left;">' . role($joueur['role']) . '</div></li>';
		}
		?>
		</ul>
	<div style="clear: both;"></div>
	<?php if(isset($log->amoureux))
	{
	echo '<p><strong>Amoureux : </strong>' .
	vraiPseudo($log->amoureux[0]) . ' et ' . vraiPseudo($log->amoureux[1])
	. '</p>';
	}

	$i = 0;
	foreach($log->tour as $tour)
	{
		$i++;
		$secondTour = false;
		echo '<h2 style="border: 1px solid black; background-color: white; padding: 5px;">Tour '. $i . '</h2>';
		
		foreach($tour->children() as $type => $noeud)
		{
			switch($type)
			{
				case('action'):
					traiterAction($noeud);
					break;
				
				case('votes'):
					traiterVotes($noeud);
					break;
					
				case('murs'):
					traiterMurs($noeud);
					break;
					
				case('spr'):
					traiterSpr($noeud);
					break;
				
				default:
					echo '<p>Inconnu !</p>';
			}
		} 
	}
	?>
	
	<h2>
	<?php
	switch($log->gagnant)
	{	
		case 'villageois':
			echo 'Les villageois remportent la partie !';
			break;
		
		case 'loups_0':
			echo 'Il n\'y a plus aucun villageois : les loups-garous remportent la partie !';
			break;
			
		case 'loups_1':
			echo 'Il n\'y a plus qu\'un villageois : les loups-garous remportent la partie !';
			
			foreach($joueurs as $joueur)
			{
				if($joueur['role'] != 'loup' && $joueur['role'] != 'maitre')
					unset($joueurs[strval($joueur)]);
			}
			
			break;
			
		case 'amoureux':
			echo 'Les amoureux remportent la partie !';
			break;
			
		case 'personne':
			echo 'La partie se termine sur un match nul !';
			break;

		case 'ange':
			echo 'L\'ange a été tué par les villageois...et remporte la partie !';

			foreach($joueurs as $joueur)
			{
				if($joueur['role'] != 'ange')
					unset($joueurs[strval($joueur)]);
			}

			break;

		default:
			echo 'Je ne sais pas qui a gagné...';
			break;
	}
	?>
	</h2>
	
	<p><strong>Survivants :</strong><br :>
	<?php
	if(sizeof($joueurs) > 0)
	{
		$survivants = '';
		
		foreach($joueurs as $joueur)
			$survivants .= strval($joueur) . ', ';
		
		echo substr($survivants, 0, -2);
	}
	else
	{
		echo 'Personne !';
	}
	?>
	</p>
	
	<?php
	
	if(isset($log->logPartie))
	{
		echo '<h2>Log de la partie</h2>';
		
		echo '<p><span class="placeduvillage">Message sur le canal de jeu</span> - <span class="loupsgarous">Message sur le canal des loups-garous</span> - <span class="mp">Message privé</span></p>';
		
		echo '<div id="chat">';
		
		foreach($log->logPartie->chat as $chat)
		{
			$texte = str_replace('<', '&lt;', str_replace('>', '&gt;', strval($chat)));
			
			if($chat['mp'] == 'true')
				echo '<span class="mp">(De &lt;<strong>'.$chat['auteur'].'&gt;</strong> à &lt;<strong>'.$chat['destination'].'</strong>&gt;) ' . $texte . '</span><br />';
			else
			{
				if(strcasecmp($chat['destination'], '#Placeduvillage') == 0)
				{
					$destination = '#PlaceDuVillage';
					$classe = 'placeduvillage';
				}
				elseif(strcasecmp($chat['destination'], '#LoupsGarous') == 0)
				{
					$destination = '#LoupsGarous';
					$classe = 'loupsgarous';
				}
				
				if($chat['auteur'] == 'MaitreDuJeu')
					 echo '<span class="'.$classe.'">&lt;<strong>'.$chat['auteur'].'</strong>&gt; <strong>' . $texte . '</strong></span><br />';
				else
					echo '<span class="'.$classe.'">&lt;<strong>'.$chat['auteur'].'</strong>&gt; ' . $texte . '</span><br />';
			}
		}
		
		echo '</div>';
	}
	
	?>
	
	<p><a href="log.php">Retour aux autres parties</a></p>
	
	</body>
</html>

# Copyright (C) 2013-2018 Jean-Francois Romang (jromang@posteo.de)
#                         Shivkumar Shivaji ()
#                         Jürgen Précour (LocutusOfPenguin@posteo.de)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# for this (picotalker) to work you need to run these commands (if you haven't done before)
# apt-get install vorbis-tools
# apt-get install sox

########################################################################
# Molli: voice comments based on Fritz audio files
#        to be activated via pico voice menue
########################################################################

import threading
import logging
import subprocess
import queue
from pathlib import Path
from shutil import which
#molli
from random import randint

import chess
from utilities import DisplayMsg
from timecontrol import TimeControl
from dgt.api import Message
from dgt.util import GameResult, PlayMode, Voice


class PicoTalker(object):

    """Handle the human speaking of events."""

    def __init__(self, localisation_id_voice, speed_factor: float):
        self.voice_path = None
        self.speed_factor = 1.0
        self.set_speed_factor(speed_factor)

        try:
            (localisation_id, voice_name) = localisation_id_voice.split(':')
            voice_path = 'talker/voices/' + localisation_id + '/' + voice_name
            if Path(voice_path).exists():
                self.voice_path = voice_path
            else:
                logging.warning('voice path [%s] doesnt exist', voice_path)
        except ValueError:
            logging.warning('not valid voice parameter')

    def set_speed_factor(self, speed_factor: float):
        """Set the speed voice factor."""
        self.speed_factor = speed_factor if which('play') else 1.0  # check for "sox" package

    def talk(self, sounds):
        """Speak out the sound part by using ogg123/play."""
        if not self.voice_path:
            logging.debug('picotalker turned off')
            return False

        vpath = self.voice_path
        result = False
        for part in sounds:
            voice_file = vpath + '/' + part
            if Path(voice_file).is_file():
                if self.speed_factor == 1.0:
                    command = ['ogg123', voice_file]
                else:
                    command = ['play', voice_file, 'tempo', str(self.speed_factor)]
                try:  # use blocking call
                    subprocess.call(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result = True
                except OSError as os_exc:
                    logging.warning('OSError: %s => turn voice OFF', os_exc)
                    self.voice_path = None
                    return False
            else:
                logging.warning('voice file not found %s', voice_file)
        return result


class PicoTalkerDisplay(DisplayMsg, threading.Thread):

    """Listen on messages for talking."""

    USER = 'user'
    COMPUTER = 'computer'
    SYSTEM = 'system'
    talkfile = ''
    rand = '' ##molli
    
    def __init__(self, user_voice: str, computer_voice: str, speed_factor: int, setpieces_voice: bool):
        """
        Initialize a PicoTalkerDisplay with voices for the user and/or computer players.

        :param user_voice: The voice to use for the user (eg. en:al).
        :param computer_voice: The voice to use for the computer (eg. en:christina).
        """
        super(PicoTalkerDisplay, self).__init__()
        self.user_picotalker = None  # type: PicoTalker
        self.computer_picotalker = None  # type: PicoTalker
        self.speed_factor = (90 + (speed_factor % 10) * 5) / 100
        self.play_mode = PlayMode.USER_WHITE
        self.low_time = False
        self.play_game = None  # saves the game after a computer move - used for "setpieces" to speak the move again
        self.setpieces_voice = setpieces_voice

        if user_voice:
            logging.debug('creating user voice: [%s]', str(user_voice))
            self.set_user(PicoTalker(user_voice, self.speed_factor))
        if computer_voice:
            logging.debug('creating computer voice: [%s]', str(computer_voice))
            self.set_computer(PicoTalker(computer_voice, self.speed_factor))

    def set_computer(self, picotalker):
        """Set the computer talker."""
        self.computer_picotalker = picotalker

    def set_user(self, picotalker):
        """Set the user talker."""
        self.user_picotalker = picotalker

    def set_factor(self, speed_factor):
        """Set speech factor."""
        if self.computer_picotalker:
            self.computer_picotalker.set_speed_factor(speed_factor)
        if self.user_picotalker:
            self.user_picotalker.set_speed_factor(speed_factor)

    def talk(self, sounds, dev=SYSTEM):
        if self.low_time:
            return
        if False:  # switch-case
            pass
        elif dev == self.USER:
            if self.user_picotalker:
                self.user_picotalker.talk(sounds)
        elif dev == self.COMPUTER:
            if self.computer_picotalker:
                self.computer_picotalker.talk(sounds)
        elif dev == self.SYSTEM:
            if self.computer_picotalker:
                if self.computer_picotalker.talk(sounds):
                    return
            if self.user_picotalker:
                self.user_picotalker.talk(sounds)

    
    def run(self):
        """Start listening for Messages on our queue and generate speech as appropriate."""
        ## molli: number of possible comments in differrent groups
        ##        should be equal or even greater than real existing ones
        ##        By this one con control how often a comment will be spoken
        cmove_no_78  = 600 ## existing: 78 random out of 600
        chat_no_74   = 600 ## existing: 74 random out of 600
        poem_no_59   = 500 ## existing: 59 random out of 500
        umove_no_109 = 700 ## existing: 109 random out of 700
        
        previous_move = chess.Move.null()  # Ignore repeated broadcasts of a move
        logging.info('msg_queue ready')
        while True:
            try:
                # Check if we have something to say
                message = self.msg_queue.get()

                if False:  # switch-case
                    pass
                elif isinstance(message, Message.ENGINE_FAIL):
                    logging.debug('announcing ENGINE_FAIL')
                    self.talk(['error.ogg'])

                elif isinstance(message, Message.START_NEW_GAME):
                    if message.newgame:
                        logging.debug('announcing START_NEW_GAME')
                        self.talk(['newgame.ogg'])
                        self.play_game = None
                        rand = str(randint(1,30))
                        talkfile = 'f_newgame' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                        rand = str(randint(1,50))
                        talkfile = 'f_uwhite' + rand + '.ogg'
                        self.talk([talkfile]) #molli

                elif isinstance(message, Message.COMPUTER_MOVE):
                    if message.move and message.game and message.move != previous_move:
                        logging.debug('announcing COMPUTER_MOVE [%s]', message.move)
                        game_copy = message.game.copy()
                        game_copy.push(message.move)
                        self.talk(self.say_last_move(game_copy), self.COMPUTER)
                        rand = str(randint(1,cmove_no_78))
                        talkfile = 'f_cmove' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                        previous_move = message.move
                        self.play_game = game_copy

                elif isinstance(message, Message.COMPUTER_MOVE_DONE):
                    self.play_game = None
                    rand = str(randint(1,chat_no_74))
                    talkfile = 'f_chat' + rand + '.ogg'
                    self.talk([talkfile]) #molli

                elif isinstance(message, Message.USER_MOVE_DONE):
                    if message.move and message.game and message.move != previous_move:
                        logging.debug('announcing USER_MOVE_DONE [%s]', message.move)
                        self.talk(self.say_last_move(message.game), self.USER)
                        previous_move = message.move
                        self.play_game = None
                        rand = str(randint(1,umove_no_109))
                        talkfile = 'f_umove' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                        rand = str(randint(1,poem_no_59))
                        talkfile = 'f_poem' + rand + '.ogg'
                        self.talk([talkfile]) #molli

                elif isinstance(message, Message.REVIEW_MOVE_DONE):
                    if message.move and message.game and message.move != previous_move:
                        logging.debug('announcing REVIEW_MOVE_DONE [%s]', message.move)
                        self.talk(self.say_last_move(message.game), self.USER)
                        previous_move = message.move
                        self.play_game = None  # @todo why thats not set in dgtdisplay?

                elif isinstance(message, Message.GAME_ENDS):
                    if message.result == GameResult.OUT_OF_TIME:
                        logging.debug('announcing GAME_ENDS/TIME_CONTROL')
                        wins = 'whitewins.ogg' if message.game.turn == chess.BLACK else 'blackwins.ogg'
                        self.talk(['timelost.ogg', wins])
                        if wins == 'whitewins.ogg':
                            if self.play_mode == PlayMode.USER_WHITE:
                                rand = str(randint(1,19))
                                talkfile = 'f_uwin' + rand + '.ogg'
                            else:
                                rand = str(randint(1,9))
                                talkfile = 'f_uloose' + rand + '.ogg'
                        else:
                            if self.play_mode == PlayMode.USER_BLACK:
                                rand = str(randint(1,19))
                                talkfile = 'f_uwin' + rand + '.ogg'
                            else:
                                rand = str(randint(1,9))
                                talkfile = 'f_uloose' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.INSUFFICIENT_MATERIAL:
                        logging.debug('announcing GAME_ENDS/INSUFFICIENT_MATERIAL')
                        self.talk(['material.ogg', 'draw.ogg'])
                        rand = str(randint(1,2))
                        talkfile = 'f_draw' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.MATE:
                        logging.debug('announcing GAME_ENDS/MATE')
                        ##self.talk(['checkmate.ogg'])
                        ##wins = 'whitewins.ogg' if message.game.turn == chess.BLACK else 'blackwins.ogg'
                        ##self.talk([wins]) #molli
                        rand = str(randint(1,9))
                        talkfile = 'f_mate' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                        if message.game.turn == chess.BLACK:
                            # white wins
                            if self.play_mode == PlayMode.USER_WHITE:
                                self.talk(['checkmate.ogg'])
                                self.talk(['whitewins.ogg']) #molli
                                rand = str(randint(1,19))
                                talkfile = 'f_uwin' + rand + '.ogg'
                            else:
                                rand = str(randint(1,9))
                                talkfile = 'f_uloose' + rand + '.ogg'
                        else:
                            # black wins
                            if self.play_mode == PlayMode.USER_BLACK:
                                self.talk(['checkmate.ogg'])
                                self.talk(['blackwins.ogg']) #molli
                                rand = str(randint(1,19))
                                talkfile = 'f_uwin' + rand + '.ogg'
                            else:
                                rand = str(randint(1,9))
                                talkfile = 'f_uloose' + rand + '.ogg' #molli
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.STALEMATE:
                        logging.debug('announcing GAME_ENDS/STALEMATE')
                        self.talk(['stalemate.ogg'])
                        rand = str(randint(1,3))
                        talkfile = 'f_stalemate' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.ABORT:
                        logging.debug('announcing GAME_ENDS/ABORT')
                        self.talk(['abort.ogg'])
                    elif message.result == GameResult.DRAW:
                        logging.debug('announcing GAME_ENDS/DRAW')
                        self.talk(['draw.ogg'])
                        rand = str(randint(1,2))
                        talkfile = 'f_draw' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.WIN_WHITE:
                        logging.debug('announcing GAME_ENDS/WHITE_WIN')
                        self.talk(['whitewins.ogg'])
                        if self.play_mode == PlayMode.USER_WHITE:
                            rand = str(randint(1,19))
                            talkfile = 'f_uwin' + rand + '.ogg'
                        else:
                            rand = str(randint(1,9))
                            talkfile = 'f_uloose' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.WIN_BLACK:
                        logging.debug('announcing GAME_ENDS/BLACK_WIN')
                        self.talk(['blackwins.ogg'])
                        if self.play_mode == PlayMode.USER_BLACK:
                            rand = str(randint(1,19))
                            talkfile = 'f_uwin' + rand + '.ogg'
                        else:
                            rand = str(randint(1,9))
                            talkfile = 'f_uloose' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    elif message.result == GameResult.FIVEFOLD_REPETITION:
                        logging.debug('announcing GAME_ENDS/FIVEFOLD_REPETITION')
                        self.talk(['repetition.ogg', 'draw.ogg'])
                        rand = str(randint(1,2))
                        talkfile = 'f_draw' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                elif isinstance(message, Message.TAKE_BACK):
                    logging.debug('announcing TAKE_BACK')
                    self.talk(['takeback.ogg'])
                    self.play_game = None
                    previous_move = chess.Move.null()
                    rand = str(randint(1,15))
                    talkfile = 'f_takeback' + rand + '.ogg'
                    self.talk([talkfile]) #molli

                elif isinstance(message, Message.TIME_CONTROL):
                    logging.debug('announcing TIME_CONTROL')
                    self.talk(['oktime.ogg'])

                elif isinstance(message, Message.INTERACTION_MODE):
                    logging.debug('announcing INTERACTION_MODE')
                    self.talk(['okmode.ogg'])

                elif isinstance(message, Message.LEVEL):
                    if message.do_speak:
                        logging.debug('announcing LEVEL')
                        self.talk(['oklevel.ogg'])
                    else:
                        logging.debug('dont announce LEVEL cause its also an engine message')

                elif isinstance(message, Message.OPENING_BOOK):
                    logging.debug('announcing OPENING_BOOK')
                    self.talk(['okbook.ogg'])

                elif isinstance(message, Message.ENGINE_READY):
                    logging.debug('announcing ENGINE_READY')
                    self.talk(['okengine.ogg'])

                elif isinstance(message, Message.PLAY_MODE):
                    logging.debug('announcing PLAY_MODE')
                    self.play_mode = message.play_mode
                    userplay = 'userblack.ogg' if message.play_mode == PlayMode.USER_BLACK else 'userwhite.ogg'
                    self.talk([userplay])
                    if message.play_mode == PlayMode.USER_BLACK:
                        rand = str(randint(1,12))
                        talkfile = 'f_ublack' + rand + '.ogg'
                        self.talk([talkfile]) #molli
                    else:
                        rand = str(randint(1,19))
                        talkfile = 'f_uwhite' + rand + '.ogg'
                        self.talk([talkfile]) #molli

                elif isinstance(message, Message.STARTUP_INFO):
                    self.play_mode = message.info['play_mode']
                    logging.debug('announcing PICOCHESS')
                    self.talk(['picoChess.ogg'])
                    rand = str(randint(1,22))
                    talkfile = 'f_start' + rand + '.ogg'
                    self.talk([talkfile]) #molli
                    rand = str(randint(1,7))
                    talkfile = 'f_fritz' + rand + '.ogg'
                    self.talk([talkfile]) #molli

                elif isinstance(message, Message.CLOCK_TIME):
                    self.low_time = message.low_time
                    if self.low_time:
                        logging.debug('time too low, disable voice - w: %i, b: %i', message.time_white,
                                      message.time_black)

                elif isinstance(message, Message.ALTERNATIVE_MOVE):
                    self.play_mode = message.play_mode
                    self.play_game = None

                elif isinstance(message, Message.SYSTEM_SHUTDOWN):
                    logging.debug('announcing SHUTDOWN')
                    self.talk(['goodbye.ogg'])
                    rand = str(randint(1,8))
                    talkfile = 'f_shutdown' + rand + '.ogg'
                    self.talk([talkfile]) #molli

                elif isinstance(message, Message.SYSTEM_REBOOT):
                    logging.debug('announcing REBOOT')
                    self.talk(['pleasewait.ogg'])

                elif isinstance(message, Message.SET_VOICE):
                    self.speed_factor = (90 + (message.speed % 10) * 5) / 100
                    localisation_id_voice = message.lang + ':' + message.speaker
                    if message.type == Voice.USER:
                        self.set_user(PicoTalker(localisation_id_voice, self.speed_factor))
                    if message.type == Voice.COMP:
                        self.set_computer(PicoTalker(localisation_id_voice, self.speed_factor))
                    if message.type == Voice.SPEED:
                        self.set_factor(self.speed_factor)

                elif isinstance(message, Message.WRONG_FEN):
                    if self.play_game and self.setpieces_voice:
                        self.talk(self.say_last_move(self.play_game), self.COMPUTER)

                else:  # Default
                    pass
            except queue.Empty:
                pass

    @staticmethod
    def say_last_move(game: chess.Board):
        """Take a chess.BitBoard instance and speaks the last move from it."""
        move_parts = {
            'K': 'king.ogg',
            'B': 'bishop.ogg',
            'N': 'knight.ogg',
            'R': 'rook.ogg',
            'Q': 'queen.ogg',
            'P': 'pawn.ogg',
            '+': '',
            '#': '',
            'x': 'takes.ogg',
            '=': 'promote.ogg',
            'a': 'a.ogg',
            'b': 'b.ogg',
            'c': 'c.ogg',
            'd': 'd.ogg',
            'e': 'e.ogg',
            'f': 'f.ogg',
            'g': 'g.ogg',
            'h': 'h.ogg',
            '1': '1.ogg',
            '2': '2.ogg',
            '3': '3.ogg',
            '4': '4.ogg',
            '5': '5.ogg',
            '6': '6.ogg',
            '7': '7.ogg',
            '8': '8.ogg'
        }

        bit_board = game.copy()
        move = bit_board.pop()
        san_move = bit_board.san(move)
        voice_parts = []
        taken  = False #molli
        castle = False #molli
        knight = False #molli
        rook   = False #molli
        king   = False #molli
        bishop = False #molli
        pawn   = False #molli
        queen  = False #molli

        if san_move.startswith('O-O-O'):
            voice_parts += ['castlequeenside.ogg']
            castle = True
        elif san_move.startswith('O-O'):
            voice_parts += ['castlekingside.ogg']
            castle = True
        else:
            for part in san_move:
                try:
                    sound_file = move_parts[part]
                except KeyError:
                    logging.warning('unknown char found in san: [%s : %s]', san_move, part)
                    sound_file = ''
                if sound_file:
                    voice_parts += [sound_file]
                    if sound_file   == 'takes.ogg':
                        taken = True    #molli
                    elif sound_file == 'knight.ogg':
                        knight = True   #molli
                    elif sound_file == 'king.ogg':
                        king = True     #molli
                    elif sound_file == 'rook.ogg':
                        rook = True     #molli
                    elif sound_file == 'pawn.ogg':
                        pawn = True     #molli
                    elif sound_file == 'bishop.ogg':
                        bishop = True   #molli
                    elif sound_file == 'queen.ogg':
                        queen = True    #molli

        if taken:
            rand = str(randint(1,130))
            sound_file = 'f_taken' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif bishop:
            rand = str(randint(1,70))
            sound_file = 'f_bishop' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif queen:
            rand = str(randint(1,70))
            sound_file = 'f_queen' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif knight:
            rand = str(randint(1,70))
            sound_file = 'f_knight' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif rook:
            rand = str(randint(1,70))
            sound_file = 'f_rook' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif king:
            rand = str(randint(1,70))
            sound_file = 'f_king' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif castle:
            rand = str(randint(1,70))
            sound_file = 'f_castle' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        elif pawn:
            rand = str(randint(1,70))
            sound_file = 'f_pawn' + rand + '.ogg'
            voice_parts += [sound_file]   #molli
        else:
            rand = str(randint(1,70))
            sound_file = 'f_pawn' + rand + '.ogg'
            voice_parts += [sound_file]   #molli

        if game.is_game_over():
            if game.is_checkmate():
                wins = 'whitewins.ogg' if game.turn == chess.BLACK else 'blackwins.ogg'
                voice_parts += ['checkmate.ogg', wins]
            elif game.is_stalemate():
                voice_parts += ['stalemate.ogg']
            else:
                if game.is_seventyfive_moves():
                    voice_parts += ['75moves.ogg', 'draw.ogg']
                elif game.is_insufficient_material():
                    voice_parts += ['material.ogg', 'draw.ogg']
                elif game.is_fivefold_repetition():
                    voice_parts += ['repetition.ogg', 'draw.ogg']
                else:
                    voice_parts += ['draw.ogg']
        elif game.is_check():
            voice_parts += ['check.ogg']
            rand = str(randint(1,30))
            talkfile = 'f_check' + rand + '.ogg'
            voice_parts += [talkfile] #molli

        if bit_board.is_en_passant(move):
            voice_parts += ['enpassant.ogg']

        return voice_parts

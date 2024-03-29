from ovos_workshop.skills import OVOSSkill
from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
import random
import time
from ovos_workshop.decorators import resting_screen_handler
from lingua_franca.parse import extract_number
import pynstagram


class FuturismComicsSkill(OVOSSkill):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.settings.get("idle_random"):
            self.settings["idle_random"] = True
        self.cartoons = []
        self.last_sync = 0
        self.current_comic = self.total_comics()

    def initialize(self):
        self.add_event('skill-futurism-cartoons.jarbasskills.home',
                       self.handle_homescreen)
        self.gui.register_handler('skill-futurism-cartoons.jarbasskills.next',
                                  self.handle_next_comic)
        self.gui.register_handler('skill-futurism-cartoons.jarbasskills.prev',
                                  self.handle_prev_comic)

    # futurism cartoons api
    @staticmethod
    def get_posts(user="futurismcartoons", skips=None):
        # This is a list os post ids that should be skipped, usually ads
        # TODO find a mechanism other than a manually maintained list
        skips = skips or ['2135177480425138062', '2103822161740647491']
        posts = list(reversed(list(pynstagram.get_media(user))))
        post_ids = [i['item_id'] for i in posts]
        for idx, post in enumerate(post_ids):
            if post in skips:
                posts[idx] = None
        return [p for p in posts if p]

    def get_cartoons(self):
        # only sync once every 6 hours
        if time.time() - self.last_sync > 60 * 60 * 6:
            self.log.info("Retrieving futurism cartoons")
            self.cartoons = self.get_posts()
            self.last_sync = time.time()
        return self.cartoons

    def total_comics(self):
        return len(self.get_cartoons())

    # homescreen
    def handle_homescreen(self, message):
        self.current_comic = self.total_comics()
        self.display_comic()

    # idle screen
    @resting_screen_handler("futurism_cartoons")
    def idle(self):
        if not self.settings.get("idle_random"):
            number = self.total_comics()
        else:
            number = random.randint(1, self.total_comics())
        data = self.cartoons[number]
        url = data["url"]
        self.gui.show_image(url, fill='PreserveAspectFit')
        self.set_context("FUTURISM_CARTOON", number)

    # intents
    @intent_handler("futurism_total_cartoons.intent")
    def handle_total_futurism_intent(self, message):
        self.speak_dialog("futurism_total_cartoons",
                          {"number": self.total_comics()})
        self.gui.show_text(str(self.total_comics()) + " comics")

    @intent_handler("latest_futurism_cartoon.intent")
    def handle_futurism_intent(self, message):
        self.display_comic(self.total_comics())

    @intent_handler("futurism_cartoon.intent")
    def handle_futurism_comic_intent(self, message):
        number = extract_number(message.data["utterance"],
                                lang=self.lang,
                                ordinals=True)
        total = self.total_comics()
        if number > total:
            self.speak_dialog("num_error", {"total": total})
            self.gui.show_text(str(total) + " comics")
            return
        self.current_comic = number
        self.display_comic(number)

    @intent_handler("random_futurism_cartoon.intent")
    def handle_futurism_random_intent(self, message):
        number = random.randint(1, self.total_comics())
        self.display_comic(number)

    @intent_handler(
        IntentBuilder("PrevFuturismIntent").require("previous").optionally(
            "picture").require("FUTURISM_CARTOON"))
    def handle_prev_comic(self, message=None):
        number = self.current_comic - 1
        if number < 1:
            number = 1
        self.display_comic(number)

    @intent_handler(
        IntentBuilder("NextFuturismIntent").require("next").optionally(
            "picture").require("FUTURISM_CARTOON"))
    def handle_next_comic(self, message=None):
        number = self.current_comic + 1
        if number > self.total_comics():
            number = self.total_comics()
        self.display_comic(number)

    @intent_handler(
        IntentBuilder("RandomFuturismIntent").require("another").optionally(
            "picture").require("FUTURISM_CARTOON"))
    def handle_another_comic(self, message=None):
        self.handle_futurism_random_intent()

    def display_comic(self, number=None, speak=True):
        self.gui.clear()
        number = number or self.current_comic
        self.current_comic = number
        self.get_cartoons()
        data = self.cartoons[number - 1]
        self.gui['imgLink'] = data["url"]
        self.gui['title'] = "FuturismCartoons#" + str(self.total_comics())
        self.gui['caption'] = data["text"].split("\n")[0].split("#")[0]
        self.gui["raw_data"] = data
        self.gui.show_page("comic.qml", override_idle=True)
        self.set_context("FUTURISM_CARTOON", str(number))
        if speak:
            utt = data["text"].split("\n")[0].split("#")[0]
            self.speak(utt, wait=True)

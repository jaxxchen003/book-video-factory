#!/usr/bin/env python3
"""Seed the approved 2026-07-13 V4 batch with original scripts and image plans.

The only generated statements are editorial paraphrases.  Book facts and
cover records remain in each project's WeRead source pack.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import _bootstrap  # noqa: F401
from book_video_factory.scene_contract import V4_SCENE_LINE_CONTRACT


ROLES = [
    "thesis", "insight", "problem", "clarification", "reframe", "method",
    "method", "action_prompt", "result", "relationship_reframe", "closing_setup", "closing",
]
STYLE = (
    "3:4 vertical editorial portrait, cinematic realistic photography, deep black negative space, "
    "low-saturation charcoal and warm-gray palette, one restrained warm-orange practical light, "
    "soft film grain, quiet emotional tension, premium book-channel art direction, no text, "
    "no letters, no logo, no watermark, no book cover, no recognizable public figure"
)


def item(slug: str, title_en: str, author_en: str, hook: tuple[str, str], passages: list[tuple[str, str]], topics: list[tuple[str, str]], visuals: list[str], mood: str) -> dict:
    if len(passages) != 12 or len(visuals) != 12:
        raise ValueError(f"{slug} must have exactly 12 script passages and 12 visual beats")
    return {
        "slug": slug, "title_en": title_en, "author_en": author_en, "hook": hook,
        "passages": passages, "topics": topics, "visuals": visuals, "mood": mood,
    }


BATCH = [
    item(
        "nvc-marshall-rosenberg", "Nonviolent Communication", "Marshall B. Rosenberg",
        ("你以为自己在解释，别人听到的却是指责。", "You think you are explaining; the other person hears blame."),
        [
            ("冲突里最难的，常常不是没有道理。", "In conflict, the hardest part is often not being wrong."),
            ("而是我们一开口，就急着给对方下结论。", "It is how quickly we label the other person when we speak."),
            ("你从来不在乎我，和我等了很久，是两件不同的事。", "You never care and I have waited a long time are two different things."),
            ("前一句会让人防御，后一句才给关系留下入口。", "The first invites defense; the second leaves an opening."),
            ("先说看见的事实，再承认自己的感受。", "Start with what happened, then own what you feel."),
            ("接着问自己：我真正需要被看见的，是什么？", "Then ask: what is the need I want to have seen?"),
            ("最后把指责换成一个具体、可回应的请求。", "Finally, trade accusation for a concrete request someone can answer."),
            ("比如：今晚十分钟，你愿意只听我把话说完吗？", "For example: could you give me ten minutes tonight and just listen?"),
            ("沟通不是赢得一句话。", "Communication is not about winning a sentence."),
            ("是让彼此终于知道，对方正在承受什么。", "It is about finally knowing what the other person is carrying."),
            ("当你少一点判断，关系才多一点空间。", "With less judgment, a relationship gains more room."),
            ("把想证明自己对，换成想靠近彼此。", "Trade proving you are right for moving closer to each other."),
        ],
        [("观察", "OBSERVE"), ("感受", "FEEL"), ("需要", "NEED"), ("请求", "REQUEST"), ("关系", "RELATION"), ("边界", "BOUNDARY"), ("倾听", "LISTEN"), ("靠近", "CONNECT")],
        ["a woman sitting silent at a dinner table while two blurred hands gesture across from her", "a close-up of a phone chat screen reflected on a tired face, screen contents intentionally unreadable", "two cups on a kitchen table separated by a thin stripe of warm sunset light", "a man pausing before speaking in a dim hallway, hands relaxed", "a notebook with blank pages beside a cooling cup of tea", "a person looking out a rain-streaked window, soft orange lamp behind", "two people sitting apart on a sofa, their shoulders gradually turning toward each other", "a small kitchen timer beside two chairs facing one another", "a hand setting down a clenched fist and opening the palm", "a quiet table with one extra chair pulled slightly closer", "a doorway lit by warm light after a dark corridor", "two silhouettes walking slowly side by side at night"],
        "warm",
    ),
    item(
        "intimate-relationship-rowland-miller", "Intimate Relationships", "Rowland S. Miller",
        ("最让人疲惫的关系，不是争吵，是你从不敢开口。", "The most exhausting relationship is not one with arguments; it is one where you never dare to speak."),
        [
            ("你把想见面的话删掉，把委屈说成没事。", "You delete the message asking to meet, and call hurt no big deal."),
            ("你以为不提要求，关系就会更安全。", "You think having no requests will make the relationship safer."),
            ("可一个人一直猜，另一个人一直忍，都会很累。", "But one person guessing and the other enduring will exhaust both."),
            ("亲密不是读心术，也不是谁更会忍耐。", "Intimacy is not mind-reading, and it is not a contest of endurance."),
            ("它需要把模糊的不安，说成清楚的需要。", "It asks us to turn vague unease into a clear need."),
            ("不是你都不陪我。", "Not: you are never there for me."),
            ("而是这周能不能留一个晚上，只属于我们？", "But: can we keep one evening this week just for us?"),
            ("具体的请求，不会让你变麻烦。", "A specific request does not make you a burden."),
            ("它让对方终于有机会靠近真实的你。", "It gives the other person a chance to approach the real you."),
            ("好的关系，不是永远没有失望。", "A good relationship is not one with no disappointment."),
            ("而是失望出现时，仍能被好好说出来。", "It is one where disappointment can still be spoken with care."),
            ("别再把沉默，当成爱的证据。", "Do not keep treating silence as proof of love."),
        ],
        [("亲密", "INTIMACY"), ("需要", "NEED"), ("表达", "SPEAK"), ("信任", "TRUST"), ("关系", "RELATION"), ("回应", "RESPONSE"), ("靠近", "CLOSER"), ("真实", "REAL")],
        ["a person typing a message on a phone then pausing before sending, unreadable screen", "two dinner plates with one untouched in a dark apartment", "a couple standing in a doorway, seen only as soft silhouettes", "a folded blanket at the far end of a sofa", "a hand holding a phone close to the chest in a warm dim room", "an empty chair by a window with city lights beyond", "two cups being placed side by side on a small table", "a calendar with no readable writing, one evening marked only by a warm circle of light", "two people walking on separate sides of a quiet street and slowly converging", "a close view of hands almost touching across a table", "a couple speaking softly in silhouette, reflected in a dark window", "a lamp left on in a quiet room after a conversation"],
        "tender",
    ),
    item(
        "stop-internal-woshan", "Stop Internal Friction", "Ruo Shan",
        ("让你累的，往往不是事情本身，是事情结束后你还在审判自己。", "What drains you is often not the task, but the self-trial that continues after it ends."),
        [
            ("一封邮件发出去，你又反复点开。", "After sending one email, you open it again and again."),
            ("一句话说完，你开始想自己是不是很笨。", "After one sentence, you begin wondering whether you sounded foolish."),
            ("事情已经结束，脑子却不肯下班。", "The task is over, but your mind refuses to clock out."),
            ("内耗常常披着认真和负责的外衣。", "Internal friction often wears the costume of being careful and responsible."),
            ("可反复审判，不会让已经发生的事更好。", "But replaying a trial will not improve what has already happened."),
            ("它只会偷走你留给下一件事的力气。", "It only steals the energy you need for the next thing."),
            ("试着问一句：我现在是在修正，还是在惩罚自己？", "Try asking: am I correcting something now, or punishing myself?"),
            ("能修正的，写下一个动作。", "If it can be corrected, write down one action."),
            ("不能修正的，就允许它停在今天。", "If it cannot, allow it to stop with today."),
            ("你不需要把每一次不完美，都变成一场判决。", "You do not need to turn every imperfection into a verdict."),
            ("认真不是把自己逼到没有退路。", "Being serious does not mean driving yourself into a corner."),
            ("做完以后，也该把自己还给生活。", "When you are done, give yourself back to life."),
        ],
        [("内耗", "FRICTION"), ("自责", "SELF-BLAME"), ("完成", "DONE"), ("修正", "REPAIR"), ("停下", "PAUSE"), ("松开", "RELEASE"), ("日常", "LIFE"), ("呼吸", "BREATHE")],
        ["a lone office worker under a desk lamp after everyone has left", "a computer screen with abstract unreadable blocks reflected in tired eyes", "a hand hovering over a sent-message icon on an unreadable phone", "a crumpled sticky note beside a perfectly closed laptop", "a person standing before a bathroom mirror, face half in shadow", "a wall clock at night with a warm orange second hand", "a blank checklist with one small checkmark, no readable words", "a hand closing a notebook and placing it on a shelf", "a raincoat hanging by an apartment door after work", "a person stepping from an office corridor into quiet evening light", "tea steam rising beside a switched-off laptop", "a city bus window with a tired face relaxing in reflection"],
        "reflective",
    ),
    item(
        "subjectivity-wang-hongmei", "The Sense of Deserving", "Wang Hongmei",
        ("你总怕麻烦别人，是因为把自己的需要当成了负担。", "You may fear burdening others because you have learned to treat your needs as a burden."),
        [
            ("约时间时，你总说都可以。", "When choosing a time, you always say anything works."),
            ("点餐时，你先问所有人想吃什么。", "When ordering, you ask what everyone else wants first."),
            ("轮到自己，你反而不知道想要什么。", "When it is your turn, you no longer know what you want."),
            ("这不是体贴的全部。", "That is not the whole meaning of being considerate."),
            ("有时，是你太习惯把自己从选择里撤走。", "Sometimes, you are simply used to removing yourself from the choice."),
            ("主体性，不是变得强硬。", "Agency is not becoming hard-edged."),
            ("是承认：我的感受，也可以占一个位置。", "It is admitting: my feelings can take up a place too."),
            ("下一次先说一句：我更想要这个。", "Next time, try saying: I would prefer this."),
            ("不解释太多，也不急着补偿。", "No long explanation, and no rush to compensate."),
            ("你提出需要，不等于给别人添麻烦。", "Naming a need does not mean creating trouble for others."),
            ("你只是在重新回到自己的生活里。", "You are simply returning to your own life."),
            ("那个敢说我想要的人，也值得被好好对待。", "The person who can say I want this deserves good care too."),
        ],
        [("主体性", "AGENCY"), ("配得感", "DESERVE"), ("选择", "CHOICE"), ("需要", "NEED"), ("表达", "VOICE"), ("自己", "SELF"), ("位置", "PLACE"), ("允许", "ALLOW")],
        ["a group menu on a table with one person quietly holding it closed", "a woman at a café looking at others before deciding", "a hand moving a chair slightly closer to the table", "a softly lit apartment hallway with a person standing at the threshold", "a close-up of a hand choosing one orange fruit from a bowl", "a person writing a short blank line in a notebook", "three friends at a table turning to listen to one person", "a small lamp switched on beside an empty chair", "a woman looking at her reflection with a calmer expression", "a door opening toward warm afternoon light", "a hand placing a personal mug among several shared cups", "a person walking upright through a quiet street at dawn"],
        "warm",
    ),
    item(
        "emotional-first-aid-guy-winch", "Emotional First Aid", "Guy Winch",
        ("情绪最糟的时候，最不需要的是逼自己立刻想通。", "When emotions are at their worst, the last thing you need is to force yourself to understand them at once."),
        [
            ("被拒绝以后，很多人先做的，是责怪自己。", "After rejection, many people first blame themselves."),
            ("深夜睡不着，又把那一幕重播很多遍。", "Unable to sleep at night, they replay the scene again and again."),
            ("情绪越满，思路越容易变窄。", "The fuller the emotion, the narrower thinking can become."),
            ("这时先别急着给人生下结论。", "This is not the time to make a verdict about your life."),
            ("先给它一个名字：我现在很难过，也很受伤。", "Give it a name first: I am sad now, and I am hurt."),
            ("再把问题缩小到今晚能照顾的一件事。", "Then shrink the problem to one thing you can care for tonight."),
            ("喝水、洗澡、关掉反复刷新的页面。", "Drink water, take a shower, close the page you keep refreshing."),
            ("如果可以，给一个可信任的人发一条消息。", "If you can, send a message to someone you trust."),
            ("不是为了马上得到答案。", "Not to get an answer immediately."),
            ("只是让自己不必独自困在那一刻。", "Just so you do not have to be trapped in that moment alone."),
            ("情绪需要被照看，不必被立刻消灭。", "Emotions need care; they do not need instant elimination."),
            ("等你站稳一点，再决定下一步。", "Once you are steadier, decide the next step."),
        ],
        [("情绪", "EMOTION"), ("受伤", "HURT"), ("命名", "NAME"), ("照顾", "CARE"), ("支持", "SUPPORT"), ("今晚", "TONIGHT"), ("站稳", "STEADY"), ("下一步", "NEXT")],
        ["a person sitting on the edge of a bed in a blue-black room at night", "an unreadable rejection notification glowing softly on a phone", "a bedside clock casting a long shadow", "a glass of water on a nightstand under a warm lamp", "a hand resting over the heart through a sweater", "steam from a shower drifting through a bathroom doorway", "a phone face-down beside a folded towel", "a single message bubble blurred beyond readability", "a friend waiting by a quiet café window", "two silhouettes sharing a bench under streetlight", "morning light reaching a rumpled bed", "a person opening curtains slowly at dawn"],
        "calm",
    ),
    item(
        "self-acceptance-zhou-fan", "When You Begin to Love Yourself", "Zhou Fan",
        ("真正的自我接纳，不是说我就这样了。", "Real self-acceptance is not saying: this is just how I am."),
        [
            ("它也不是放弃改变，或者假装自己没有问题。", "It is not giving up change, or pretending there is no problem."),
            ("而是不再用羞耻，逼自己向前走。", "It is refusing to use shame as the engine that pushes you forward."),
            ("做错一件事，和我是一个很糟糕的人，不是一回事。", "Making one mistake and being a terrible person are not the same thing."),
            ("前者可以修正，后者只会让你躲起来。", "The first can be repaired; the second only makes you hide."),
            ("你可以对自己诚实。", "You can be honest with yourself."),
            ("也可以不在每一次失败后，把自己说得一无是处。", "And you do not have to call yourself worthless after every failure."),
            ("试着把那句我怎么这么差，换成这一次哪里没做好。", "Try trading I am so bad for what did not go well this time?"),
            ("问题会变得具体，行动也会有出口。", "The problem becomes specific, and action finds an exit."),
            ("成长不靠持续否定自己。", "Growth does not depend on endlessly denying yourself."),
            ("它更像一次次回到自己身边。", "It is more like returning to your own side, again and again."),
            ("接纳不是停下。", "Acceptance is not stopping."),
            ("是带着不完美，仍愿意继续往前。", "It is moving forward while carrying imperfection with you."),
        ],
        [("接纳", "ACCEPT"), ("成长", "GROW"), ("羞耻", "SHAME"), ("修正", "REPAIR"), ("诚实", "HONEST"), ("温柔", "KIND"), ("行动", "ACTION"), ("继续", "FORWARD")],
        ["a person standing before a fogged mirror, face only partly visible", "a discarded draft page on a quiet desk", "a person sitting on stairs after a small setback", "a hand smoothing a wrinkled sleeve", "soft morning light falling on an unmade bed", "a close-up of a pencil erasing a small mark", "a notebook with a blank fresh page opening", "a person taking one deep breath at a window", "two pairs of shoes by an apartment door, one stepping out", "a small plant with one bent leaf in warm light", "a person walking alone on a sunlit path", "an open doorway framed by calm evening light"],
        "tender",
    ),
    item(
        "allowing-li-mengji", "Allow Everything to Happen", "Li Mengji",
        ("你不必等状态变好，才允许生活继续。", "You do not have to wait until you feel better before allowing life to continue."),
        [
            ("很多焦虑，都藏在一个字里：等。", "A lot of anxiety hides inside one word: wait."),
            ("等回复，等结果，等一个足够确定的答案。", "Wait for a reply, a result, an answer certain enough."),
            ("可越想把结果握紧，心越容易悬着。", "The tighter you grip the outcome, the more suspended your heart can feel."),
            ("我们能投入的，和我们能控制的，从来不是一回事。", "What we can invest in and what we can control have never been the same thing."),
            ("你可以认真准备，也可以允许结果暂时未知。", "You can prepare seriously and still allow the result to remain unknown."),
            ("你可以等消息，但不用把整天都押在消息上。", "You can wait for a message without betting your whole day on it."),
            ("把今天能做的一件小事，先做完。", "Finish one small thing that belongs to today."),
            ("去吃饭，出门走十分钟，回一通该回的电话。", "Eat, walk outside for ten minutes, return one call you need to make."),
            ("生活不是等一切确定后，才开始。", "Life does not begin only after everything becomes certain."),
            ("它正在不确定里，一点一点往前。", "It is moving forward, little by little, inside uncertainty."),
            ("允许发生，不是放弃投入。", "Allowing things to happen is not abandoning effort."),
            ("是把自己从结果里，慢慢带回今天。", "It is gently bringing yourself back from the result to today."),
        ],
        [("允许", "ALLOW"), ("等待", "WAIT"), ("未知", "UNKNOWN"), ("今天", "TODAY"), ("投入", "INVEST"), ("呼吸", "BREATHE"), ("生活", "LIFE"), ("继续", "CONTINUE")],
        ["a person waiting beside a phone in a softly lit room", "rain moving slowly down a window with city lights beyond", "a closed mailbox in a quiet apartment hallway", "hands resting on a table rather than refreshing a phone", "a person tying shoes by the front door", "a bowl of warm food on a small kitchen table", "a figure walking beneath trees in light rain", "an unreadable phone placed in a pocket", "a sunlit patch moving across a floor", "a kettle beginning to steam", "a person watering a plant near a window", "a wide view of a quiet river moving at dusk"],
        "calm",
    ),
    item(
        "procrastination-jane-burk", "The Psychology of Procrastination", "Jane B. Burka and Lenora M. Yuen",
        ("你拖着不做的，可能不是任务，而是任务背后那种怕失败的感觉。", "What you postpone may not be the task, but the fear of failing that sits behind it."),
        [
            ("打开文档，又关掉。", "You open the document, then close it."),
            ("想开始的那一刻，身体却先去刷别的东西。", "At the moment you mean to begin, your body reaches for something else."),
            ("这不一定是懒。", "That is not necessarily laziness."),
            ("有时，是大脑在躲一个太大的感受。", "Sometimes, your brain is avoiding a feeling that seems too large."),
            ("怕做不好，怕被评价，怕发现自己不够好。", "Fear of doing badly, being judged, or finding you are not enough."),
            ("所以先别只问：我为什么这么拖？", "So do not only ask: why do I procrastinate so much?"),
            ("也问问：我究竟在躲什么？", "Also ask: what am I actually avoiding?"),
            ("把第一步缩小到两分钟也能完成。", "Shrink the first step until it can be done in two minutes."),
            ("只写标题，只打开文件，只摆好材料。", "Write only the title, open only the file, lay out only the materials."),
            ("开始不需要壮烈。", "Starting does not need to be dramatic."),
            ("它只需要比逃开，再轻一点。", "It only needs to feel a little lighter than running away."),
            ("今天先做小到不会害怕的第一步。", "Today, take a first step small enough not to frighten you."),
        ],
        [("拖延", "DELAY"), ("开始", "START"), ("害怕", "FEAR"), ("两分钟", "TWO MIN"), ("缩小", "SMALLER"), ("行动", "ACTION"), ("完成", "DONE"), ("前进", "FORWARD")],
        ["a laptop open to a blank unreadable document in a dark room", "a finger hovering over a keyboard without typing", "a phone face-down beside an unfinished notebook", "a person looking at a wall clock from a desk", "a stack of materials arranged but untouched", "a small orange timer set beside a laptop", "a hand writing one short blank line on paper", "a folder being opened on a clean desktop", "a person taking off headphones and returning to the desk", "a single desk lamp creating a focused circle of light", "a close-up of one checked box without any readable text", "a person closing the laptop calmly after a small start"],
        "focused",
    ),
    item(
        "inferiority-adler", "Inferiority and Transcendence", "Alfred Adler",
        ("自卑最隐蔽的样子，不是觉得自己差，而是永远不敢开始。", "The most hidden form of inferiority is not feeling lesser; it is never daring to begin."),
        [
            ("看到别人的成果，你先想到的是：我肯定不行。", "When you see someone else’s work, your first thought is: I could never do that."),
            ("于是作品写到一半删掉，机会来了也先退后。", "So you delete work halfway through and step back when an opportunity arrives."),
            ("比较久了，别人就像标准，你只剩下被评分。", "After enough comparison, other people become the standard and you become only the score."),
            ("可比较从来不是事实本身。", "But comparison is never the fact itself."),
            ("它只是让你忘了，每个人都在不同的位置开始。", "It only makes you forget that everyone begins from a different place."),
            ("你不必先变得毫不自卑，才配行动。", "You do not have to become completely confident before you deserve to act."),
            ("先做一件能留下痕迹的小事。", "Start with one small act that leaves a trace."),
            ("发出草稿，练十分钟，完成一个微小的承诺。", "Send the draft, practice for ten minutes, keep one small promise."),
            ("自信不是站在起点前等来的。", "Confidence does not arrive while you wait at the starting line."),
            ("它常常是在做过以后，才慢慢长出来。", "It often grows slowly after you have done something."),
            ("别把别人的完成，变成自己的退场。", "Do not turn someone else’s completion into your exit."),
            ("回到你今天还可以积累的那一步。", "Return to the step you can still build today."),
        ],
        [("自卑", "INFERIOR"), ("比较", "COMPARE"), ("开始", "BEGIN"), ("积累", "BUILD"), ("勇气", "COURAGE"), ("草稿", "DRAFT"), ("自己", "SELF"), ("一步", "STEP")],
        ["a person scrolling through abstract achievement images on a phone, no readable content", "a crumpled drawing beside a clean blank sheet", "a person standing outside a bright studio door, hesitant", "two staircases at different distances in a dark architectural space", "a small unfinished clay object on a worktable", "a hand pressing send on a deliberately unreadable draft", "a person practicing alone in a softly lit room", "one shoe stepping onto the first stair", "a small notebook with a single page turned", "sunlight landing on an unfinished but cared-for object", "a figure walking past a glowing billboard without looking at it", "a quiet path with small footprints leading forward"],
        "reflective",
    ),
    item(
        "burnout-society-byung-chul-han", "The Burnout Society", "Byung-Chul Han",
        ("你累的不是工作量，而是连休息都觉得自己不够努力。", "You may not be tired only from workload, but from feeling unproductive even while resting."),
        [
            ("深夜还回消息，假期也在给自己安排任务。", "You answer messages late at night and schedule tasks even on holidays."),
            ("看起来是自由，其实像没有人允许你停。", "It looks like freedom, yet it feels as if no one allows you to stop."),
            ("最难察觉的压力，是你开始自己催促自己。", "The hardest pressure to notice is when you begin pushing yourself."),
            ("事情做完了，心里仍有一个声音说：还不够。", "Even when the work is done, a voice says: still not enough."),
            ("于是休息也变成了需要打卡的项目。", "Then even rest becomes an item that must be checked off."),
            ("先别急着再安排一个更高效的晚上。", "Do not rush to plan an even more efficient evening."),
            ("给自己留一个没有产出的空白时段。", "Leave yourself a blank period that produces nothing."),
            ("不回最后一条消息，不把散步变成学习。", "Do not answer the final message; do not turn a walk into study."),
            ("不是所有时间，都要证明它有价值。", "Not every hour has to prove its value."),
            ("你不是一台永远要升级的机器。", "You are not a machine that must always be upgraded."),
            ("真正的停下，不是奖励。", "Real stopping is not a reward."),
            ("它是让你还能继续生活的基本条件。", "It is a basic condition for being able to keep living."),
        ],
        [("倦怠", "BURNOUT"), ("休息", "REST"), ("证明", "PROVE"), ("停下", "STOP"), ("空白", "SPACE"), ("夜晚", "NIGHT"), ("生活", "LIFE"), ("呼吸", "BREATHE")],
        ["a person alone at a desk surrounded by dark screens at midnight", "an unreadable stream of notifications glowing on a phone", "a calendar-like grid with no readable text filling an entire wall", "a tired face reflected in a dark laptop screen", "a pair of walking shoes beside a desk rather than outside", "a lamp switched off in a room still lit by monitor glow", "a person sitting on a balcony with no device in hand", "an empty park bench under a single warm streetlamp", "a kettle and two cups in a quiet kitchen", "a notebook closed under a small stone", "sunlight moving slowly across a bare floor", "a person walking without a bag toward an open horizon"],
        "reflective",
    ),
]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def seed(project: Path, spec: dict) -> None:
    source_pack_path = project / "01_research_资料搜集/normalized/book_source_pack.json"
    source = json.loads(source_pack_path.read_text(encoding="utf-8"))
    book = source["book"]
    lines = [
        {"id": "V01", "role": "hook", "zh": spec["hook"][0], "en": spec["hook"][1]},
        {"id": "V02", "role": "reveal_cue", "zh": "它来自——", "en": "It comes from—"},
        {
            "id": "V03", "role": "book_reveal",
            "zh": f"{book['author']}的《{book['title']}》。",
            "en": f"{spec['title_en']}, by {spec['author_en']}.",
        },
    ]
    for index, ((zh, en), role) in enumerate(zip(spec["passages"], ROLES, strict=True), start=4):
        lines.append({"id": f"V{index:02d}", "role": role, "zh": zh, "en": en})
    script = {
        "schema_version": "2.0",
        "project_id": spec["slug"],
        "version": "v4-approved-2026-07-13",
        "status": "approved_for_production",
        "book": {
            "title": book["title"], "author": book["author"],
            "english_display_title": spec["title_en"],
            "english_title_status": "editorial_translation_not_official",
        },
        "voice_profile": "book_channel_b_female_warm_healing_v1",
        "translation_status": "production_draft_needs_native_review",
        "intro_topics": [{"zh": zh, "en": en} for zh, en in spec["topics"]],
        "lines": lines,
        "full_text": "".join(line["zh"] for line in lines),
    }
    write_json(project / "02_story_script_故事脚本/script.v2.bilingual.json", script)
    evidence = {
        "schema_version": "1.0", "project_id": spec["slug"],
        "script": "script.v2.bilingual.json",
        "source_pack": "../01_research_资料搜集/normalized/book_source_pack.json",
        "claim_mappings": [
            {"lines": ["V01", "V02", "V03"], "basis": "Book identity and editorial hook; no direct quotation.", "source_locations": ["book.title", "book.author"], "quote_usage": "original_paraphrase"},
            {"lines": ["V04", "V05", "V06", "V07", "V08", "V09"], "basis": "Editorial paraphrase grounded in the book introduction and chapter outline.", "source_locations": ["book.intro", "chapter_outline"], "quote_usage": "original_paraphrase"},
            {"lines": ["V10", "V11", "V12", "V13", "V14", "V15"], "basis": "Original, low-risk daily-life prompts inspired by the book's themes; not treatment, diagnosis, or a promise of results.", "source_locations": ["book.intro", "chapter_outline", "public_reviews"], "quote_usage": "original_paraphrase"},
        ],
        "editorial_notes": [
            "No popular highlight or public review is quoted verbatim.",
            "This video is editorial commentary, not medical, psychological treatment, or diagnostic advice.",
            "English captions are a production draft and need native-language review before public release.",
        ],
    }
    write_json(project / "02_story_script_故事脚本/script_evidence.json", evidence)
    scene_plan = {
        "schema_version": "1.0", "project_id": spec["slug"], "style": STYLE,
        "render_target": "approved/v4/S01.png ... S12.png",
        "scenes": [
            {
                "id": f"S{index:02d}",
                "line_ids": list(V4_SCENE_LINE_CONTRACT[f"S{index:02d}"]),
                "prompt": f"{STYLE}; {visual}",
            }
            for index, visual in enumerate(spec["visuals"], start=1)
        ],
    }
    write_json(project / "03_images_生成图片/prompts/v4_scene_plan.json", scene_plan)
    (project / "03_images_生成图片/approved/v4").mkdir(parents=True, exist_ok=True)
    brief = {
        "schema_version": "1.0", "project_id": spec["slug"], "approved_at": datetime.now(UTC).isoformat(),
        "approval": "User approved full V4 production for the 2026-07-13 batch.",
        "topic": spec["hook"][0], "book": {"title": book["title"], "author": book["author"], "weread_book_id": book.get("book_id")},
        "bgm_mood": spec["mood"], "asset_rules": {"unique_scenes": 12, "project_specific_bgm": True, "real_cover": True},
    }
    write_json(project / "00_topic_选题/topic_brief.json", brief)
    (project / "04_copy_文案/publish_copy.draft.md").write_text(
        f"# 《{book['title']}》\n\n{spec['hook'][0]}\n\n#读书 #自我成长 #{book['title']}\n",
        encoding="utf-8",
    )
    project_meta = json.loads((project / "project.json").read_text(encoding="utf-8"))
    project_meta.update({"status": "seeded_for_v4_production", "current_stage": "02_script_and_assets", "book": {"title": book["title"], "author": book["author"]}})
    write_json(project / "project.json", project_meta)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed all ten approved V4 projects")
    parser.add_argument("--warehouse", type=Path, required=True)
    args = parser.parse_args()
    warehouse = args.warehouse.resolve()
    for spec in BATCH:
        project = warehouse / "projects" / spec["slug"]
        if not project.is_dir():
            raise FileNotFoundError(project)
        seed(project, spec)
    library = {
        "schema_version": "1.0", "approved_at": datetime.now(UTC).isoformat(),
        "name": "2026-07-13-v4-batch-10", "status": "in_production",
        "projects": [{"project_id": spec["slug"], "english_title": spec["title_en"], "bgm_mood": spec["mood"]} for spec in BATCH],
    }
    write_json(warehouse / "topic_library/approved/2026-07-13-v4-batch-10.json", library)
    print(json.dumps({"seeded_projects": len(BATCH), "library": str(warehouse / "topic_library/approved/2026-07-13-v4-batch-10.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

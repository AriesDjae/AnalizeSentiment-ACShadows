from acs_sentiment import text


def test_clean_text_removes_urls_contractions_and_symbols():
    raw = "I DON'T like it!! See https://example.com/x 10/10 www.foo.bar"
    assert text.clean_text(raw) == "i dont like it see"


def test_clean_text_handles_empty_values():
    assert text.clean_text(None) == ""
    assert text.tokenize("   ") == []


def test_content_tokens_drops_stopwords_noise_and_short_tokens():
    tokens = text.tokenize("The game is ok but the combat and stealth are great")
    assert text.content_tokens(tokens) == ["combat", "stealth", "great"]


def test_lexicon_score_counts_positive_and_negative_seeds():
    assert text.lexicon_score(text.tokenize("great story, amazing world")) == 2
    assert text.lexicon_score(text.tokenize("buggy and boring")) == -2
    assert text.lexicon_score(text.tokenize("good visuals but repetitive")) == 0


def test_lexicon_score_flips_polarity_after_negation():
    assert text.lexicon_score(text.tokenize("It's not good")) == -1
    assert text.lexicon_score(text.tokenize("I don't recommend it")) == -1
    assert text.lexicon_score(text.tokenize("never boring")) == 1


def test_negation_only_applies_within_window():
    # "not" berada > 3 token sebelum "good"
    assert text.lexicon_score(text.tokenize("not the first one but this is good")) == 1


def test_label_from_score():
    assert text.label_from_score(3) == "positive"
    assert text.label_from_score(-1) == "negative"
    assert text.label_from_score(0) == "neutral"


def test_looks_english_keeps_english_including_terse_reviews():
    assert text.looks_english("good game")
    assert text.looks_english("this is one of the best games i have played in years")
    assert text.looks_english("Good gameplay, bad story, very bad assassins creed game")
    assert text.looks_english("Very pretty, good stealth, good combat, bad voice acting")


def test_looks_english_rejects_other_languages():
    assert not text.looks_english("das Spiel ist wirklich gut und die Grafik sieht fantastisch aus")
    assert not text.looks_english("Se você curte Assassin's Creed na fórmula atual, vai gostar muito deste jogo")
    assert not text.looks_english("Biraz oynayım dedim, oyun bitti. Oyuna karşı çok nefret var")
    assert not text.looks_english("分數：8 / 10，傳奇的戰國日本，風雲地，英雄地。絕美的大和風光")

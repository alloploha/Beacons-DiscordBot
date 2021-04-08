BABEL := pybabel
POT_DIR := locale
LANGUAGES := en ru
OUTPUT_DIR ?= out
POT := $(addprefix $(POT_DIR)/, messages.pot)

all: translation output

$(POT) &: *.py
	$(BABEL) extract . -o $@

%.mo: %.po
	$(BABEL) compile --directory $(POT_DIR) --locale=$(call extract_language, $@)

PO := $(foreach language, $(LANGUAGES), $(POT_DIR)/$(language)/LC_MESSAGES/messages.po)

define extract_language 
$(strip \
	$(strip \
		$(foreach language, $(LANGUAGES), \
			$(findstring $(language), $1)
		)
	)
)
endef

$(PO): $(POT)
	$(BABEL) update -i $(POT) -d $(POT_DIR) -l $(call extract_language, $@)

MO := $(PO:.po=.mo) 

translation: $(MO)

output:
	-robocopy . $(OUTPUT_DIR) *.py *.txt *.mo /XD $(OUTPUT_DIR) /XD .* /S

.PHONY: all translation output

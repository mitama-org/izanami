from mitama.app.forms import Form, Field, DictField

class MergeCreateForm(Form):
    title = Field(label='要約', required=True)
    body = Field(label='メッセージ', required=True)
    base = Field(label='ベース', required=True)
    compare = Field(label='マージ対象', required=True)

class SettingsForm(Form):
    role = DictField(listed=True)



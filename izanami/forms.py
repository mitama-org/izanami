from mitama.app.forms import Form, Field

class HookUpdateForm(Form):
    name = Field(label='フック名', required=True)
    code = Field(label='コード', required=True)

class HookCreateForm(Form):
    name = Field(label='フック名', required=True)
    code = Field(label='コード', required=True)

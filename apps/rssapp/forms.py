from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
    UserCreationForm,
)

from .models import Bookmark, Feed, Tag, UserProfile

User = get_user_model()

_INPUT_CLASS = (
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm "
    "placeholder-gray-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 "
    "focus:outline-none transition-colors"
)


class FeedCreateForm(forms.ModelForm):
    class Meta:
        model = Feed
        fields = ["name", "url", "category"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": _INPUT_CLASS, "placeholder": "Feed name"}
            ),
            "url": forms.URLInput(
                attrs={
                    "class": _INPUT_CLASS,
                    "placeholder": "https://example.com/rss.xml",
                }
            ),
            "category": forms.TextInput(
                attrs={"class": _INPUT_CLASS, "placeholder": "Category (optional)"}
            ),
        }


class FeedUpdateForm(forms.ModelForm):
    class Meta:
        model = Feed
        fields = ["name", "url", "category", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT_CLASS}),
            "url": forms.URLInput(attrs={"class": _INPUT_CLASS}),
            "category": forms.TextInput(
                attrs={"class": _INPUT_CLASS, "placeholder": "Uncategorized"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500",
                }
            ),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": _INPUT_CLASS, "placeholder": "Tag name"}
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "h-9 w-14 rounded-lg border border-gray-200 cursor-pointer",
                    "type": "color",
                }
            ),
        }


class BookmarkForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": _INPUT_CLASS,
                "placeholder": "tag1, tag2, tag3",
            }
        ),
    )

    class Meta:
        model = Bookmark
        fields = ["url", "title", "description"]
        widgets = {
            "url": forms.URLInput(
                attrs={
                    "class": _INPUT_CLASS,
                    "placeholder": "https://example.com",
                    "id": "bookmark-url",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": _INPUT_CLASS,
                    "placeholder": "Page title",
                    "id": "bookmark-title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": _INPUT_CLASS,
                    "placeholder": "Description (optional)",
                    "rows": 3,
                    "id": "bookmark-description",
                }
            ),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["default_sort", "items_per_page", "theme_preference"]
        widgets = {
            "default_sort": forms.Select(
                attrs={
                    "class": _INPUT_CLASS,
                }
            ),
            "items_per_page": forms.NumberInput(
                attrs={
                    "class": _INPUT_CLASS,
                    "min": "5",
                    "max": "100",
                }
            ),
            "theme_preference": forms.Select(
                attrs={
                    "class": _INPUT_CLASS,
                }
            ),
        }


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": _INPUT_CLASS,
                "placeholder": "you@example.com",
                "autofocus": True,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs.update(
            {
                "class": _INPUT_CLASS,
                "placeholder": "Password",
            }
        )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": _INPUT_CLASS,
                "placeholder": "you@example.com",
                "autofocus": True,
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {
                "class": _INPUT_CLASS,
                "placeholder": "Create a password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": _INPUT_CLASS,
                "placeholder": "Confirm your password",
            }
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(DjangoPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = _INPUT_CLASS

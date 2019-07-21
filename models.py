from peewee import SqliteDatabase, IntegerField, Model, DateTimeField, CharField, ForeignKeyField, BooleanField
from datetime import datetime

db = SqliteDatabase('users.db')


def time_format():
    return datetime.now().strftime('%y.%m.%d %H:%M:%S.%f')[:-4]


class User(Model):
    class Meta:
        database = db
        db_table = "users"

    user_id = IntegerField()
    username = CharField(null=True)
    full_name = CharField(null=True)

    house = IntegerField(null=True)
    section = IntegerField(null=True)
    floor = IntegerField(null=True)
    apartment = IntegerField(null=True)

    created = DateTimeField(default=time_format)
    updated = DateTimeField(default=None, null=True)
    
    @property
    def href(self):
        """ inline mention of a user. works only after user write to bot first
            <a href="tg://user?id=<user_id>">inline mention of a user</a>"""
        return f'🔹<a href="tg://user?id={self.user_id}">{self.full_name}</a>'
        
    @property
    def floor_(self):
        """for 2-level floors. split integer from db in format 11-12"""
        return str(self.floor)[0:2] + '-' + str(self.floor)[2:4] if ((self.floor or 1) > 99) else self.floor
        
    @property
    def username_(self):
        """if no username return empty string"""
        return '@' + self.username if self.username else ''

    def __str__(self):
        if self.apartment:
            return f'{self.href} {self.username_}     {self.floor_ or "?"} пов. {self.apartment} кв.'
        else:
            return f'{self.href} {self.username_}     {self.floor_ or "?"} пов.'

    def setting_str(self):
        return f'Будинок <b>{self.house}</b> п-зд <b>{self.section or "?"}</b> поверх ' \
            f'<b>{self.floor_ or "?"}</b> кв. <b>{self.apartment or "?"}</b>'

    def edit_btn_str(self):
        return f'Будинок {self.house} п-зд {self.section or "?"} пов. {self.floor_ or "?"} кв. {self.apartment or "?"}'

    def user_created(self):
        if self.apartment:
            return f'{self.href} {self.username_} буд. {self.house} п-зд {self.section or "?"} пов. {self.floor_ or "?"} кв. {self.apartment} id {self.user_id}'
        else:
            return f'{self.href} {self.username_} буд. {self.house} п-зд {self.section or "?"} пов. {self.floor_ or "?"} id {self.user_id}'

    def joined_str(self):
        if self.apartment:
            return f'{self.href} {self.username_}   {self.house} буд. {self.section} п-зд  {self.floor_ or "?"} пов. {self.apartment} кв.'
        else:
            return f'{self.href} {self.username_}   {self.house} буд. {self.section} п-зд  {self.floor_ or "?"} пов.'


class Show(Model):
    class Meta:
        database = db
        db_table = "params"

    user_id = IntegerField()

    house = IntegerField(null=True)
    section = IntegerField(null=True)
    floor = IntegerField(null=True)

    owns = IntegerField(null=True)

    msg_apart_mode = BooleanField(null=True, default=False)
    notification_mode = CharField(null=True, default=None)

    def __str__(self):
        return f'{self.user_id} - {self.house} : {self.section}-{self.floor}'


class Jubilee(Model):
    class Meta:
        database = db
        db_table = "jubilee"

    house = IntegerField()
    count = IntegerField()
    celebrated = DateTimeField(default=time_format)


if __name__ == '__main__':
    db.create_tables([User, Show, Jubilee], safe=True)

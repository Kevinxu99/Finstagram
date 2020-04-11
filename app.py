from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="root",
                             db="finsta",
                             charset="utf8mb4",
                             port=8889,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/images", methods=["GET", "POST"])
@login_required
def images():
    query = "SELECT * FROM Photo WHERE (photoOwner IN (SELECT followeeUsername FROM Follow WHERE followerUsername = %s and acceptedfollow = 1) and allFollowers = 1) OR (photoID IN (SELECT photoID FROM Belong NATURAL JOIN Share WHERE username = %s and acceptedInvite = 1)) OR (photoOwner = %s) ORDER BY timestamp DESC"
    with connection.cursor() as cursor:
        cursor.execute(query, (session["username"], session["username"], session["username"]))
    data = cursor.fetchall()
    query = "SELECT * FROM Tag WHERE acceptedTag = 1"
    with connection.cursor() as cursor:
        cursor.execute(query)
    dataTag = cursor.fetchall()
    if request.args.get("photoID") :
        photoID = request.args.get("photoID")
        func = request.args.get("func")
        if func == "like":
            query = "INSERT INTO Liked (username, photoID, timestamp) VALUES (%s, %s, %s)"
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, (session["username"], photoID, time.strftime('%Y-%m-%d %H:%M:%S')))
            except pymysql.err.IntegrityError:
                return render_template("images.html", images=data, message2="Photo Already Liked")
            return render_template("images.html", images=data, message2="Like Sccuessful")
        if func == "comment":
            commentText = request.form["comment"]
            query = "INSERT INTO Comment (username, photoID, commentText, timestamp) VALUES (%s, %s, %s, %s)"
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, (session["username"], photoID, commentText, time.strftime('%Y-%m-%d %H:%M:%S')))
            except pymysql.err.IntegrityError:
                return render_template("images.html", images=data, message2="You Already Commented")
            return render_template("images.html", images=data, message2="Comment Sccuessful")
    if request.form:
        requestData = request.form
        if requestData["taggee"] and requestData["photo"]:
            taggee = requestData["taggee"]
            photoID = requestData["photo"]
            if session["username"] == taggee :
                try:
                    query = "INSERT INTO Tag (username, photoID, acceptedTag) VALUES (%s, %s, %s)"
                    with connection.cursor() as cursor:
                        cursor.execute(query, (session["username"], photoID, 1))
                except pymysql.err.IntegrityError:
                    return render_template("images.html", images=data, message1="User Already Tagged")
            query = "SELECT * FROM photo WHERE photoID = %s and ((photoOwner IN (SELECT followeeUsername FROM Follow WHERE followerUsername = %s and acceptedfollow = 1) and allFollowers = 1) OR (photoID IN (SELECT photoID FROM Belong NATURAL JOIN Share WHERE username = %s and acceptedInvite = 1)) OR (photoOwner = %s))"
            with connection.cursor() as cursor:
                cursor.execute(query, (photoID, taggee, taggee, taggee))
            dataTest = cursor.fetchall()
            if dataTest:
                try:
                    query = "INSERT INTO Tag (username, photoID, acceptedTag) VALUES (%s, %s, %s)"
                    with connection.cursor() as cursor:
                        cursor.execute(query, (taggee, photoID, 0))
                except pymysql.err.IntegrityError:
                    return render_template("images.html", images=data, message1="User Already Tagged")
            else:
                return render_template("images.html", images=data, message1="Invalid Tag")
            return render_template("images.html", images=data, message1="Tag Successful")
#        if request.form["liked"]:
#            likedPhoto = requestData["like"]
#
    return render_template("images.html", images=data)

@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)
        
#        if request.files:
#            image_file = request.files.get("imageToUpload", "")
#            image_name = image_file.filename
#            filepath = os.path.join(IMAGES_DIR, image_name)
#            image_file.save(filepath)
#            with connection.cursor() as cursor:
#                query = "UPDATE person SET avatar = %s WHERE username = %s"
#                cursor.execute
#
        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["POST","GET"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        caption=""
        if request.form:
            requestData = request.form
            caption=requestData["caption"]
            allFollowers = requestData["public"]
        query = "INSERT INTO photo (photoOwner, timestamp, filePath, caption, allFollowers) VALUES (%s, %s, %s, %s, %s)"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (session["username"], time.strftime('%Y-%m-%d %H:%M:%S'), image_name, caption, allFollowers))
        except:
            message = "Failed to upload image."
            return render_template("upload.html", message=message)
        message = "Image has been successfully uploaded."
        return render_template("upload.html", message=message)
    else:
        return render_template("upload.html")


@app.route("/share", methods=["GET", "POST"])
@login_required
def share():
    with connection.cursor() as cursor:
        query = "SELECT * FROM Belong WHERE username = %s"
        cursor.execute(query, session["username"])
    dataGroup = cursor.fetchall()
    with connection.cursor() as cursor:
        query = "SELECT * FROM Photo WHERE photoOwner = %s and allFollowers= %s"
        cursor.execute(query, (session["username"],"0"))
    dataPhoto = cursor.fetchall()
    if request.form:
        requestData = request.form
        photoID = requestData["photoID"]
        groupName = requestData["group"]
        with connection.cursor() as cursor:
            query = "SELECT groupOwner FROM Belong WHERE groupName = %s and username = %s"
            cursor.execute(query, (groupName, session["username"]))
        data = cursor.fetchone()
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Share (groupName, groupOwner, photoID) VALUES (%s, %s, %s)"
                cursor.execute(query, (groupName, data["groupOwner"], photoID))
        except pymysql.err.IntegrityError:
            error = "Failed to share"
            return render_template("share.html", photos=dataPhoto, groups=dataGroup, message=error)
        return render_template("share.html", photos=dataPhoto, groups=dataGroup, message= "Photo successfully shared.")
    return render_template("share.html", photos=dataPhoto, groups=dataGroup)


@app.route("/follow", methods=["GET", "POST"])
@login_required
def follow():
    if request.form:
        requestData = request.form
        followee = requestData["followee"]
        follower = session["username"]
        with connection.cursor() as cursor:
            query = "SELECT * FROM Person WHERE username = %s"
            cursor.execute(query, followee)
        data = cursor.fetchone()
        if data:
            with connection.cursor() as cursor:
                query = "INSERT INTO Follow (followerUsername, followeeUsername, acceptedfollow) VALUES (%s, %s, %s)"
                cursor.execute(query, (follower, followee, 0))
        else:
            error = "Username does not exist."
            return render_template("follow.html", error=error)
    return render_template("follow.html")

@app.route("/followRequests", methods=["GET", "POST"])
@login_required
def followRequests():
    if request.form:
        requestData = request.form
        query = requestData["query"]
        with connection.cursor() as cursor:
            cursor.execute(query, session["username"])
    query = "SELECT * FROM Follow WHERE followeeUsername = %s AND acceptedfollow = 0"
    with connection.cursor() as cursor:
            cursor.execute(query, session["username"])
    data = cursor.fetchall()
    return render_template("followRequest.html", requests = data)

@app.route("/tag", methods=["GET","POST"])
@login_required
def tagRequests():
    if request.form:
        requestData = request.form
        query = requestData["query"]
        with connection.cursor() as cursor:
            cursor.execute(query, session["username"])
    query = "SELECT * FROM Tag NATURAL JOIN Photo WHERE username = %s AND acceptedTag = 0"
    with connection.cursor() as cursor:
        cursor.execute(query, session["username"])
    data = cursor.fetchall()
    return render_template("tag.html", requests = data)

@app.route("/taggee", methods=["GET"])
@login_required
def taggees():
    photoID = request.args.get("photoID")
    query = "SELECT * FROM Tag NATURAL JOIN Person WHERE photoID = %s AND acceptedTag = 1"
    with connection.cursor() as cursor:
        cursor.execute(query, photoID)
    data = cursor.fetchall()
    return render_template("taggee.html", taggees = data)

@app.route("/closefriendgroup", methods=["GET"])
@login_required
def closeFriendGroup():
    return render_template("CFG.html")

@app.route("/newgroup", methods=["GET","POST"])
@login_required
def newGroup():
    if request.form:
        requestData = request.form
        groupname = requestData["groupname"]
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO CloseFriendGroup (groupName, groupOwner) VALUES (%s, %s)"
                cursor.execute(query, (groupname, session["username"]))
        except pymysql.err.IntegrityError:
            error = "Group already exists"
            return render_template("newgroup.html", error=error)
        with connection.cursor() as cursor:
            query = "INSERT INTO Belong (groupName, groupOwner, username, acceptedInvite) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (groupname, session["username"], session["username"], 1))
    return render_template("newgroup.html")

@app.route("/addfriend", methods=["GET","POST"])
@login_required
def addFriend():
    with connection.cursor() as cursor:
        query = "SELECT * FROM CloseFriendGroup WHERE groupOwner = %s"
        cursor.execute(query, session["username"])
    data = cursor.fetchall()
    if request.form:
        requestData = request.form
        group = requestData["group"]
        friend = requestData["friend"]
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Belong (groupName, groupOwner, username, acceptedInvite) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (group, session["username"], friend, 0))
        except pymysql.err.IntegrityError:
            error = "Person already in the group"
            return render_template("addfriend.html", groups=data, error=error)
    return render_template("addfriend.html", groups=data)

@app.route("/invite", methods=["GET", "POST"])
@login_required
def invite():
    if request.form:
        requestData = request.form
        query = requestData["query"]
        with connection.cursor() as cursor:
            cursor.execute(query, session["username"])
    query = "SELECT * FROM Belong WHERE username = %s AND acceptedInvite = 0"
    with connection.cursor() as cursor:
        cursor.execute(query, session["username"])
    data = cursor.fetchall()
    return render_template("invite.html", invites = data)

@app.route("/unfollow", methods=["GET","POST"])
@login_required
def unfollow():
    if request.form:
        requestData = request.form
        userdel = requestData['friend']
        with connection.cursor() as cursor:
            querycheck = "SELECT * FROM FOLLOW WHERE followerUsername = %s AND followeeUsername = %s AND acceptedfollow = 1"
            cursor.execute(querycheck, (session["username"], userdel))
            data = cursor.fetchone()
            if data:
                with connection.cursor() as cursor:
                    query = "DELETE FROM FOLLOW WHERE followerUsername = %s AND followeeUsername = %s"
                    cursor.execute(query, (session["username"], userdel))
                    done = "Done unfollowing"
            else:
                done = "You do not follow this user"
            return render_template("unfollow.html", done=done)
    return render_template("unfollow.html")

@app.route("/like", methods = ["GET"])
@login_required
def likes():
    photoID = request.args.get("photoID")
    query = "SELECT * FROM Liked NATURAL JOIN Person WHERE photoID = %s ORDER BY timestamp DESC"
    with connection.cursor() as cursor:
        cursor.execute(query, photoID)
    data = cursor.fetchall()
    return render_template("likes.html", likes = data)

@app.route("/comment", methods = ["GET"])
@login_required
def comments():
    photoID = request.args.get("photoID")
    query = "SELECT * FROM Comment NATURAL JOIN Person WHERE photoID = %s ORDER BY timestamp DESC"
    with connection.cursor() as cursor:
        cursor.execute(query, photoID)
    data = cursor.fetchall()
    return render_template("comments.html", comments = data)

if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()


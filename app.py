from flask import Flask, request, redirect, session, url_for, g, render_template

import requests
from urllib.parse import urlencode
from base64 import encode, b64encode
from dotenv import dotenv_values

app = Flask(__name__)

secrets = dotenv_values(".env")
app.secret_key = secrets["flaskSessionSecret"]

spotifyRedirectURI = "http://localhost:5000/spotifyconnect"
spotifyReauthToken = ""

authString = secrets['spotifyClientID'] + ":" + secrets["spotifyClientSecret"]
spotifyAuthHeader = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "Basic " + str(b64encode(authString.encode("ascii")), 'utf-8')
}
spotifyAPIHeader = {}

# todo:
#   commit
#   move away from localhost, make able to access via server
#   further error handling??
#   realtime monitoring


# main loop; shows the name and song if can auth, otherwise user input required to resubmit request
@app.route("/", methods=["GET", "POST"])
def index():
    if 'spotifyToken' in session and session["spotifyToken"] != None:
        getBasicSpotifyInfo()
        return render_template("index.html")

    return """
            <h1>Request spotify token:</h1>
            <form action="/spotifyconnect" method="post">
                <input type="submit" value="Request">
            </form>
            """

# handles the initial authentication for spotify
@app.route("/spotifyconnect", methods=["GET", "POST"])
def handleSpotify():

    # handles the second part of the auth request - after auth code gotten.
    if request.args.get("code") != None:
        print("spotify code gotten")
        spotifyCode = request.args.get("code")
        params = {
            "grant_type": "authorization_code",
            "code": spotifyCode,
            "redirect_uri": spotifyRedirectURI
        }
        r = requests.post("https://accounts.spotify.com/api/token", headers=spotifyAuthHeader, data=params)
        session["spotifyToken"] = r.json().get("access_token")
        spotifyReauthToken = r.json().get("refresh_token")
        spotifyAPIHeader["Authorization"] = "Bearer " + session["spotifyToken"]

        getBasicSpotifyInfo()
        return redirect(url_for('index'))

    # starts the spotify auth procedure by redirecting user to spotify website
    if request.method == "POST":
        params = {
            "response_type": "code",
            "client_id": secrets["spotifyClientID"],
            "scope": "user-modify-playback-state user-read-currently-playing, user-read-playback-state",
            "redirect_uri": spotifyRedirectURI
        }
        return redirect("https://accounts.spotify.com/authorize?" + urlencode(params))

    return request.form


@app.route("/spotifyinfo", methods=["GET", "POST"])
def spotifyInfo():
    option = request.args.get("action", None)
    if option == None:
        return None
    elif option == "togglePlayback":
        if g.get("isSpotifyPlaying"):
            r = spotifyReq("PUT", "me/player/play")
            if r.status_code == 204:
                g.isSpotifyPlaying = False
                return True
            else:
                return False
        else:
            r = spotifyReq("PUT", "me/player/pause")
            if r.status_code == 204:
                g.isSpotifyPlaying = False
                return True
            else:
                return False
    return False


# gets basic username/song playing and attempts to refresh auth if broken
def getBasicSpotifyInfo():
    r = spotifyReq("GET", "me")
    if r.status_code == 200:
        session["spotifyName"] = r.json().get("display_name")
    elif r.status_code == 401:
        print("attempting reauth")
        if spotifyReauthToken != "":
            print("found reauth token")
            refreshSpotifyToken(spotifyReauthToken)
        else:
            print("failed; restarting from scratch")
            session["spotifyToken"] = None
            return redirect(url_for("index"))
    else:
        print("error getting basic info, code: " + str(r.status_code))
        print(">> " + r.json().get("error").get("message"))

    r = spotifyReq(reqType="GET", req="me/player")
    rjson = r.json()
    if r.status_code == 200:
        if rjson.get("is_playing"):
            g.isSpotifyPlaying = True
            songhref = rjson.get("item").get("href")
            r2 = requests.get(songhref, headers=spotifyAPIHeader)
            if r2.json().get("name") != None:
                print("got a song: " + r2.json().get("name"))
                session["currentSong"] = r2.json().get("name") + " on " + rjson.get("device").get("name")
        else:
            g.isSpotifyPlaying = False
            session["currentSong"] = None


# Use the auth tokens to get a new access token for spotify api
def refreshSpotifyToken(refreshToken):
    payload = {"grant_type": "refresh_token",
               "refresh_token": refreshToken
               }
    r = requests.post("https://accounts.spotify.com/api/token", headers=spotifyAuthHeader, data=payload)
    # spotifyToken = r.json() # TODO: do something with the 1 hour expiration timer - refresh the cred?
    if r.json().get("error") != None:
        print("ERROR: " + r.json().get("error"))
        print(">> " + r.json().get("error_description"))
    elif r.json().get("access_token") != None:
        session["spotifyToken"] = r.json().get("access_token")

        spotifyAPIHeader = {
            "Authorization": "Bearer " + session["spotifyToken"]
        }

        return True
    else:
        print("error with refreshing the spotify token")
        return False


def spotifyReq(reqType, req, data=None):
    if reqType == "GET":
        return requests.get("https://api.spotify.com/v1/"+req, headers=spotifyAPIHeader)
    elif reqType == "POST":
        return requests.post("https://api.spotify.com/v1/"+req, headers=spotifyAPIHeader, data=data)
    elif reqType == "PUT":
        return requests.put("https://api.spotify.com/v1/"+req, headers=spotifyAPIHeader, data=data)
    else:
        print("FUCK")
    return None

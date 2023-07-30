import requests
from flask import Flask, request, redirect, session, url_for
from urllib.parse import urlencode
from dotenv import dotenv_values

secrets = dotenv_values(".env")


# gets basic username/song playing and attempts to refresh auth if broken
def getBasicSpotifyInfo(spotifyAPIHeader, ):
    r = requests.get("https://api.spotify.com/v1/me", headers=spotifyAPIHeader)
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

    r = requests.get("https://api.spotify.com/v1/me/player", headers=spotifyAPIHeader)
    rjson = r.json()
    if r.status_code == 200:
        if rjson.get("is_playing"):
            songhref = rjson.get("item").get("href")
            r2 = requests.get(songhref, headers=spotifyAPIHeader)
            if r2.json().get("name") != None:
                print("got a song: " + r2.json().get("name"))
                session["currentSong"] = r2.json().get("name") + " on " + rjson.get("device").get("name")
        else:
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

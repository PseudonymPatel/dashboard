var isPlaying = false
var currentTimestamp = 0


function populateAll() {
	return 0
}

function refreshSpotify() {

}

async function progressBar() {

}


function nextSong() {

}

function prevSong() {

}

function toggleSongPlaying() {
	fetch("/spotifyinfo?action=togglePlayback")
		.then((response) => console.log(response.json))
}



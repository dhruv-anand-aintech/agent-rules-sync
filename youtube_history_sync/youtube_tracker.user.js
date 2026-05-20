// ==UserScript==
// @name         YouTube Watch History Local Sync
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automatically posts watched YouTube videos to a local FastAPI server
// @author       Antigravity
// @match        https://www.youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    let lastVideoId = null;

    function getCleanChannelName() {
        // Attempt to find the channel name in various YouTube DOM layouts
        const channelElement = document.querySelector("#upload-info #channel-name a") || 
                               document.querySelector(".ytd-channel-name a") ||
                               document.querySelector("a.yt-formatted-string[href^='/@']");
        return channelElement ? channelElement.textContent.trim() : "Unknown Channel";
    }

    function getCleanVideoTitle() {
        const titleElement = document.querySelector("h1.ytd-watch-metadata") || 
                             document.querySelector("h1.title.style-scope.ytd-video-primary-info-renderer");
        return titleElement ? titleElement.textContent.trim() : "Unknown Title";
    }

    function syncVideoToLocal(videoId) {
        if (!videoId) return;

        // Give the DOM a moment to render the title and channel name after navigation
        setTimeout(() => {
            const title = getCleanVideoTitle();
            const channel = getCleanChannelName();
            const url = `https://www.youtube.com/watch?v=${videoId}`;
            
            console.log(`[History Sync] Sending video to local server: "${title}" by "${channel}"`);

            GM_xmlhttpRequest({
                method: "POST",
                url: "http://127.0.0.1:8000/history",
                headers: {
                    "Content-Type": "application/json"
                },
                data: JSON.stringify({
                    video_id: videoId,
                    title: title,
                    url: url,
                    channel: channel,
                    timestamp: new Date().toISOString()
                }),
                onload: function(response) {
                    console.log("[History Sync] Server response:", response.responseText);
                },
                onerror: function(err) {
                    console.warn("[History Sync] Failed to connect to local server. Is webhook_history.py running?", err);
                }
            });
        }, 3000); // 3 second delay to ensure elements are present
    }

    // Hook into YouTube's SPA navigation finish event
    window.addEventListener("yt-navigate-finish", function(event) {
        const urlParams = new URLSearchParams(window.location.search);
        const videoId = urlParams.get("v");
        
        if (videoId && videoId !== lastVideoId) {
            lastVideoId = videoId;
            syncVideoToLocal(videoId);
        }
    });

    // Also check on initial page load if starting directly on a video page
    const urlParams = new URLSearchParams(window.location.search);
    const videoId = urlParams.get("v");
    if (videoId) {
        lastVideoId = videoId;
        syncVideoToLocal(videoId);
    }
})();

/**
 * Agent Composer Page - Interactive Agent Composition and Testing
 * Provides a focused environment for composing agents with role/domain combinations
 * and testing their capabilities before deployment
 */

"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Paper,
  Typography,
} from "@mui/material";
import {
  Info as InfoIcon,
  Launch as DeployIcon,
  Science as StudioIcon,
} from "@mui/icons-material";

import {
  AgentComposerStudio,
  type AgentComposition,
} from "@/components/feature/agent-composer-studio";

export default function ComposerPage() {
  const [composedAgents, setComposedAgents] = useState<AgentComposition[]>([]);
  const [deployDialogOpen, setDeployDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentComposition | null>(
    null,
  );

  const handleAgentComposed = (composition: AgentComposition) => {
    setComposedAgents((prev) => [...prev, composition]);
  };

  const handleDeployAgent = (agent: AgentComposition) => {
    setSelectedAgent(agent);
    setDeployDialogOpen(true);
  };

  const confirmDeploy = () => {
    if (selectedAgent) {
      // TODO: Integrate with actual deployment system
      console.log("Deploying agent:", selectedAgent);
      // Remove from local list after deployment
      setComposedAgents((prev) => prev.filter((a) => a !== selectedAgent));
    }
    setDeployDialogOpen(false);
    setSelectedAgent(null);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
          <StudioIcon sx={{ fontSize: 32, color: "primary.main" }} />
          <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
            Agent Composer Studio
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Interactive environment for composing agents with role/domain
          combinations and testing their capabilities
        </Typography>
      </Box>

      {/* Instructions */}
      <Alert severity="info" sx={{ mb: 4 }}>
        <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
          Welcome to the Agent Composer Studio MVP
        </Typography>
        <Typography variant="body2">
          1. Select a role and domain expertise to define your agent's
          behavioral archetype and knowledge area
          <br />
          2. Provide task context to help validate agent capabilities
          <br />
          3. Test capabilities to verify the agent can handle your requirements
          <br />
          4. Compose and deploy your agent when satisfied with the configuration
        </Typography>
      </Alert>

      <Grid container spacing={4}>
        {/* Main Composer Interface */}
        <Grid item xs={12} lg={8}>
          <AgentComposerStudio onAgentComposed={handleAgentComposed} />
        </Grid>

        {/* Composed Agents Panel */}
        <Grid item xs={12} lg={4}>
          <Paper
            sx={{ p: 3, height: "fit-content", position: "sticky", top: 24 }}
          >
            <Typography
              variant="h6"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <DeployIcon color="primary" />
              Composed Agents ({composedAgents.length})
            </Typography>

            {composedAgents.length === 0
              ? (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    Composed agents will appear here. Use the studio to create
                    your first agent.
                  </Typography>
                </Alert>
              )
              : (
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Ready for deployment
                  </Typography>

                  {composedAgents.map((agent, index) => (
                    <Paper
                      key={index}
                      variant="outlined"
                      sx={{
                        p: 2,
                        mb: 2,
                        backgroundColor: "rgba(76, 175, 80, 0.05)",
                        borderColor: "success.main",
                        borderWidth: 1,
                        "&:hover": {
                          backgroundColor: "rgba(76, 175, 80, 0.1)",
                        },
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        fontWeight={600}
                        gutterBottom
                      >
                        {agent.role}+{agent.domain}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 1, fontSize: "0.8rem" }}
                      >
                        {agent.taskContext.length > 80
                          ? `${agent.taskContext.substring(0, 80)}...`
                          : agent.taskContext}
                      </Typography>

                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 2, display: "block" }}
                      >
                        {agent.expectedCapabilities.length}{" "}
                        capabilities configured
                      </Typography>

                      <Button
                        variant="contained"
                        size="small"
                        fullWidth
                        startIcon={<DeployIcon />}
                        onClick={() => handleDeployAgent(agent)}
                      >
                        Deploy Agent
                      </Button>
                    </Paper>
                  ))}
                </Box>
              )}
          </Paper>
        </Grid>
      </Grid>

      {/* Deployment Confirmation Dialog */}
      <Dialog
        open={deployDialogOpen}
        onClose={() => setDeployDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <DeployIcon color="primary" />
          Deploy Agent
        </DialogTitle>

        <DialogContent>
          {selectedAgent && (
            <Box>
              <Typography variant="body1" gutterBottom>
                Are you ready to deploy this agent to the orchestration system?
              </Typography>

              <Paper sx={{ p: 2, mt: 2, backgroundColor: "grey.50" }}>
                <Typography variant="subtitle2" fontWeight={600}>
                  Agent Configuration:
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <strong>Role:</strong> {selectedAgent.role}
                </Typography>
                <Typography variant="body2">
                  <strong>Domain:</strong> {selectedAgent.domain}
                </Typography>
                <Typography variant="body2">
                  <strong>Task Context:</strong> {selectedAgent.taskContext}
                </Typography>
                <Typography variant="body2">
                  <strong>Capabilities:</strong>{" "}
                  {selectedAgent.expectedCapabilities.length} configured
                </Typography>
              </Paper>

              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  This agent will be available in the orchestration system and
                  can be spawned for task execution.
                </Typography>
              </Alert>
            </Box>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setDeployDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={confirmDeploy}
            startIcon={<DeployIcon />}
          >
            Deploy Agent
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
